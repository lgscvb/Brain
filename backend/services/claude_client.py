"""
Brain - AI 客戶端
支援 OpenRouter (推薦) 和 Anthropic 直連兩種模式
實作 LLM Routing 模型分流功能
"""
import json
from typing import Dict, Optional
from openai import AsyncOpenAI
from anthropic import Anthropic
from config import settings


class ClaudeClient:
    """AI API 客戶端 - 支援 OpenRouter 和 Anthropic"""

    def __init__(self):
        """初始化客戶端"""
        self.mock_mode = False
        self.provider = settings.AI_PROVIDER
        self.model = settings.CLAUDE_MODEL
        self.openrouter_client = None
        self.anthropic_client = None

        # 根據 Provider 設定初始化
        if self.provider == "openrouter":
            if not settings.OPENROUTER_API_KEY:
                print("警告：OPENROUTER_API_KEY 未設定，使用模擬模式")
                self.mock_mode = True
            else:
                self.openrouter_client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=settings.OPENROUTER_API_KEY,
                    default_headers={
                        "HTTP-Referer": "https://brain.yourspce.org",
                        "X-Title": "Hour Jungle Brain"
                    }
                )
                print(f"✅ OpenRouter 客戶端已初始化")
                print(f"   Smart Model: {settings.MODEL_SMART}")
                print(f"   Fast Model: {settings.MODEL_FAST}")
        else:
            # Anthropic 直連模式
            if not settings.ANTHROPIC_API_KEY:
                print("警告：ANTHROPIC_API_KEY 未設定，使用模擬模式")
                self.mock_mode = True
            else:
                self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                print(f"✅ Anthropic 客戶端已初始化，模型: {self.model}")

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """
        穩健的 JSON 解析，處理各種格式的 LLM 回應

        支援：
        - 純 JSON
        - Markdown code block 包裹的 JSON
        - 有前後文字的 JSON
        """
        import re

        content = content.strip()

        # 嘗試 1：直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 嘗試 2：移除 markdown code blocks
        if "```" in content:
            # 提取 code block 內容
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    pass

        # 嘗試 3：尋找 JSON 物件（{ ... }）
        match = re.search(r'\{[\s\S]*"draft"[\s\S]*\}', content)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 嘗試 4：找第一個 { 到最後一個 }
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(content[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass

        # 全部失敗
        print(f"⚠️ JSON 解析失敗，原始內容前 200 字: {content[:200]}")
        return None

    async def route_task(self, message: str) -> Dict:
        """
        [LLM Routing 第一步] 路由分析：判斷任務複雜度
        使用 Smart Model 進行精準判斷
        """
        from brain.prompts import build_router_prompt

        if self.mock_mode:
            return {"complexity": "COMPLEX", "reason": "模擬模式", "suggested_intent": "其他"}

        if not settings.ENABLE_ROUTING:
            # 未啟用分流，全部使用 Smart Model
            return {"complexity": "COMPLEX", "reason": "分流未啟用", "suggested_intent": "其他"}

        try:
            prompt = build_router_prompt(message)

            if self.provider == "openrouter":
                response = await self.openrouter_client.chat.completions.create(
                    model=settings.MODEL_SMART,
                    messages=[
                        {"role": "system", "content": "You are a task router. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=200
                )
                content = response.choices[0].message.content
                # 提取用量資訊
                usage = {
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                    "model": settings.MODEL_SMART
                }
            else:
                # Anthropic 直連
                response = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=200,
                    temperature=0.0,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": self.model
                }

            # 嘗試解析 JSON（使用穩健的解析方法）
            result = self._parse_json_response(content)
            if result:
                result["_usage"] = usage
                return result
            else:
                return {
                    "complexity": "COMPLEX",
                    "reason": "JSON解析失敗",
                    "suggested_intent": "其他",
                    "_usage": usage
                }

        except Exception as e:
            print(f"❌ 路由判斷失敗，預設為複雜模式: {e}")
            return {"complexity": "COMPLEX", "reason": f"分析失敗: {str(e)[:20]}", "suggested_intent": "其他"}

    async def generate_draft(
        self,
        message: str,
        sender_name: str,
        source: str,
        context: Optional[Dict] = None,
        model: str = None,
        conversation_history: str = "",
        rag_context: str = "",
        customer_context: str = ""
    ) -> Dict:
        """
        [LLM Routing 第二步] 生成回覆草稿
        可指定使用特定模型

        Args:
            conversation_history: 格式化的對話歷史字串
            rag_context: RAG 檢索的相關知識
            customer_context: CRM 客戶資料（來自 Jungle）
        """
        from brain.prompts import build_draft_prompt

        # 決定使用哪個模型
        if self.provider == "openrouter":
            target_model = model or settings.MODEL_SMART
        else:
            target_model = self.model

        # 模擬模式
        if self.mock_mode:
            return {
                "intent": "詢價",
                "strategy": "SPIN-S 了解客戶現況（模擬模式）",
                "draft": f"您好～因為登記需要經過經濟部和國稅局，需要先了解您目前的情況：\n\n請問您是新設立還是遷址呢？（已有統編請直接提供）\n\n方便 LINE 通話跟您確認嗎？",
                "next_action": "等待客戶回覆基本資訊",
                "_usage": {"input_tokens": 0, "output_tokens": 0, "model": "mock"}
            }

        # 建立提示詞（包含對話歷史 + RAG 知識 + 客戶資料）
        prompt = build_draft_prompt(
            content=message,
            sender_name=sender_name,
            source=source,
            conversation_history=conversation_history,
            rag_context=rag_context,
            customer_context=customer_context
        )

        try:
            if self.provider == "openrouter":
                # 建立 API 參數
                api_params = {
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful customer service assistant for Hour Jungle shared office. Output JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 16000 if settings.ENABLE_EXTENDED_THINKING else 2000
                }

                # OpenRouter 支援 reasoning 參數（適用於 Claude 3.7+, Sonnet 4.5 等）
                if settings.ENABLE_EXTENDED_THINKING:
                    api_params["extra_body"] = {
                        "reasoning": {
                            "max_tokens": settings.THINKING_BUDGET_TOKENS
                        }
                    }
                    print(f"🧠 啟用 Extended Thinking (budget: {settings.THINKING_BUDGET_TOKENS} tokens)")

                response = await self.openrouter_client.chat.completions.create(**api_params)
                content = response.choices[0].message.content
                usage = {
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                    "model": target_model
                }
            else:
                # Anthropic 直連
                api_params = {
                    "model": target_model,
                    "max_tokens": 16000 if settings.ENABLE_EXTENDED_THINKING else 2000,
                    "temperature": 0.7,
                    "messages": [{"role": "user", "content": prompt}]
                }

                if settings.ENABLE_EXTENDED_THINKING:
                    api_params["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": settings.THINKING_BUDGET_TOKENS
                    }

                response = self.anthropic_client.messages.create(**api_params)
                content = response.content[0].text
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": target_model
                }

            # 嘗試解析 JSON（更穩健的解析）
            result = self._parse_json_response(content)
            if result is None:
                # 解析失敗，嘗試提取純文字作為草稿
                clean_content = content.strip()
                # 移除 markdown code blocks
                if "```" in clean_content:
                    import re
                    clean_content = re.sub(r'```(?:json)?\s*', '', clean_content)
                    clean_content = clean_content.replace('```', '').strip()
                result = {
                    "intent": "其他",
                    "strategy": "系統自動生成（JSON解析失敗）",
                    "draft": clean_content,
                    "next_action": "人工審核"
                }

            result["_usage"] = usage
            return result

        except Exception as e:
            raise Exception(f"AI API 調用失敗 ({target_model}): {str(e)}")

    async def analyze_modification(
        self,
        original: str,
        final: str
    ) -> str:
        """
        分析人工修改原因
        """
        from brain.prompts import MODIFICATION_ANALYSIS_PROMPT

        if self.mock_mode:
            return "調整語氣，使回覆更親切自然（模擬模式）"

        prompt = MODIFICATION_ANALYSIS_PROMPT.format(
            original=original,
            final=final
        )

        try:
            if self.provider == "openrouter":
                # 分析用 Fast Model 就夠了
                response = await self.openrouter_client.chat.completions.create(
                    model=settings.MODEL_FAST,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=200
                )
                return response.choices[0].message.content.strip()
            else:
                response = self.anthropic_client.messages.create(
                    model=self.model,
                    max_tokens=200,
                    temperature=0.5,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text.strip()

        except Exception as e:
            return f"分析失敗: {str(e)}"


# 全域 Claude 客戶端實例
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """取得 Claude 客戶端單例"""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
