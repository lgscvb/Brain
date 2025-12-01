"""
Brain - Claude API 客戶端
封裝 Anthropic Claude API 調用
"""
import json
from typing import Dict, Optional
from anthropic import Anthropic
from config import settings


class ClaudeClient:
    """Claude API 客戶端"""
    
    def __init__(self):
        """初始化 Claude 客戶端"""
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY 未設定")
        
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20241022"
    
    async def generate_draft(
        self,
        message: str,
        sender_name: str,
        source: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        生成回覆草稿
        
        Args:
            message: 客戶訊息內容
            sender_name: 發送者名稱
            source: 訊息來源 (line_oa, email, phone, manual)
            context: 額外上下文資訊
        
        Returns:
            {
                "intent": "詢價|預約|客訴|閒聊|報修|其他",
                "strategy": "回覆策略說明（給操作者看）",
                "draft": "回覆草稿內容",
                "next_action": "建議下一步行動"
            }
        """
        from brain.prompts import DRAFT_PROMPT
        
        # 建立提示詞
        prompt = DRAFT_PROMPT.format(
            sender_name=sender_name,
            source=source,
            content=message
        )
        
        try:
            # 呼叫 Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # 解析回應
            content = response.content[0].text
            
            # 嘗試解析 JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # 如果無法解析 JSON，提取內容
                result = {
                    "intent": "其他",
                    "strategy": "系統自動生成",
                    "draft": content,
                    "next_action": "人工審核"
                }
            
            return result
            
        except Exception as e:
            raise Exception(f"Claude API 調用失敗: {str(e)}")
    
    async def analyze_modification(
        self,
        original: str,
        final: str
    ) -> str:
        """
        分析人工修改原因
        
        Args:
            original: AI 原始草稿
            final: 人工修改後的最終內容
        
        Returns:
            修改原因分析（30字內）
        """
        from brain.prompts import MODIFICATION_ANALYSIS_PROMPT
        
        # 建立提示詞
        prompt = MODIFICATION_ANALYSIS_PROMPT.format(
            original=original,
            final=final
        )
        
        try:
            # 呼叫 Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.5,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # 回傳分析結果
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
