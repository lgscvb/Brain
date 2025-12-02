"""
Brain - 草稿生成器
整合 LLM Routing 意圖分類與 AI API 生成回覆草稿
支援模型分流：簡單任務用便宜模型，複雜任務用高級模型
支援對話上下文：取得同一客戶的歷史對話記錄
"""
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from db.models import Message, Draft, Response, APIUsage
from services.claude_client import get_claude_client
from brain.router import get_intent_router
from api.routes.usage import calculate_cost
from config import settings


class DraftGenerator:
    """草稿生成器 - 支援 LLM Routing 和對話上下文"""

    def __init__(self):
        """初始化草稿生成器"""
        self.claude_client = get_claude_client()
        self.intent_router = get_intent_router()

    async def get_conversation_history(
        self,
        db: AsyncSession,
        sender_id: str,
        current_message_id: int
    ) -> str:
        """
        取得同一客戶的對話歷史

        Args:
            db: 資料庫連線
            sender_id: 發送者 ID（用來識別同一客戶）
            current_message_id: 當前訊息 ID（排除此訊息）

        Returns:
            格式化的對話歷史字串
        """
        limit = settings.CONVERSATION_HISTORY_LIMIT

        # 取得此客戶最近的訊息（不包含當前訊息）
        result = await db.execute(
            select(Message)
            .where(Message.sender_id == sender_id)
            .where(Message.id != current_message_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        recent_messages = result.scalars().all()

        if not recent_messages:
            return ""

        # 反轉順序，讓最舊的在前面
        recent_messages = list(reversed(recent_messages))

        # 建立對話歷史格式
        history_parts = ["## 對話歷史（最近 {} 則）\n".format(len(recent_messages))]

        for msg in recent_messages:
            # 取得此訊息的回覆（如果有）
            response_result = await db.execute(
                select(Response)
                .where(Response.message_id == msg.id)
                .order_by(desc(Response.sent_at))
                .limit(1)
            )
            response = response_result.scalar_one_or_none()

            # 格式化時間
            time_str = msg.created_at.strftime("%m/%d %H:%M") if msg.created_at else ""

            # 加入客戶訊息
            history_parts.append(f"**[{time_str}] 客戶：**\n{msg.content}\n")

            # 如果有回覆，加入回覆內容
            if response and response.final_content:
                history_parts.append(f"**[回覆] Hour Jungle：**\n{response.final_content}\n")

        history_parts.append("\n---\n\n")
        return "\n".join(history_parts)

    async def generate(
        self,
        db: AsyncSession,
        message_id: int,
        content: str,
        sender_name: str,
        source: str,
        sender_id: str = ""
    ) -> Draft:
        """
        生成草稿 - 支援 LLM Routing 模型分流 + 對話上下文

        流程：
        1. 取得對話歷史（同一客戶的最近 N 則對話）
        2. 先用 Smart Model 判斷任務複雜度
        3. 根據複雜度選擇模型
        4. 執行草稿生成（包含對話上下文）
        5. 記錄 API 用量
        """
        try:
            # === 第零步：取得對話歷史 ===
            conversation_history = ""
            if sender_id:
                conversation_history = await self.get_conversation_history(
                    db=db,
                    sender_id=sender_id,
                    current_message_id=message_id
                )
                if conversation_history:
                    print(f"📜 載入對話歷史 (sender_id: {sender_id[:20]}...)")

            # === 第一步：LLM Routing 分流判斷 ===
            routing_result = await self.claude_client.route_task(content)
            complexity = routing_result.get("complexity", "COMPLEX")
            routing_reason = routing_result.get("reason", "")
            suggested_intent = routing_result.get("suggested_intent", "其他")

            # 記錄 Router 的 API 用量
            router_usage = routing_result.get("_usage")
            if router_usage and router_usage.get("input_tokens", 0) > 0:
                router_api_usage = APIUsage(
                    provider="openrouter" if settings.AI_PROVIDER == "openrouter" else "anthropic",
                    model=router_usage.get("model", "unknown"),
                    operation="routing",
                    input_tokens=router_usage.get("input_tokens", 0),
                    output_tokens=router_usage.get("output_tokens", 0),
                    total_tokens=router_usage.get("input_tokens", 0) + router_usage.get("output_tokens", 0),
                    estimated_cost=calculate_cost(
                        router_usage.get("model", "default"),
                        router_usage.get("input_tokens", 0),
                        router_usage.get("output_tokens", 0)
                    ),
                    success=True
                )
                db.add(router_api_usage)

            # === 第二步：決定使用的模型 ===
            if complexity == "SIMPLE":
                target_model = settings.MODEL_FAST
                strategy_prefix = f"⚡ 快速模式 ({routing_reason})"
                print(f"🤖 [SIMPLE] 使用 Fast Model: {target_model}")
            else:
                target_model = settings.MODEL_SMART
                strategy_prefix = f"🧠 深度模式 ({routing_reason})"
                print(f"🤖 [COMPLEX] 使用 Smart Model: {target_model}")

            # === 第三步：生成草稿（含對話上下文）===
            draft_result = await self.claude_client.generate_draft(
                message=content,
                sender_name=sender_name,
                source=source,
                context={"intent": suggested_intent, "routing": routing_result},
                model=target_model if settings.AI_PROVIDER == "openrouter" else None,
                conversation_history=conversation_history
            )

            # === 第四步：記錄生成的 API 用量 ===
            usage_info = draft_result.pop("_usage", None)
            if usage_info:
                api_usage = APIUsage(
                    provider="openrouter" if settings.AI_PROVIDER == "openrouter" else "anthropic",
                    model=usage_info.get("model", "unknown"),
                    operation="draft_generation",
                    input_tokens=usage_info.get("input_tokens", 0),
                    output_tokens=usage_info.get("output_tokens", 0),
                    total_tokens=usage_info.get("input_tokens", 0) + usage_info.get("output_tokens", 0),
                    estimated_cost=calculate_cost(
                        usage_info.get("model", "default"),
                        usage_info.get("input_tokens", 0),
                        usage_info.get("output_tokens", 0)
                    ),
                    success=True
                )
                db.add(api_usage)

            # === 第五步：組合策略說明並儲存 ===
            ai_strategy = draft_result.get("strategy", "")
            final_strategy = f"{strategy_prefix}\n{ai_strategy}"

            draft = Draft(
                message_id=message_id,
                content=draft_result.get("draft", ""),
                strategy=final_strategy,
                intent=draft_result.get("intent", suggested_intent),
                is_selected=False
            )

            db.add(draft)
            await db.commit()
            await db.refresh(draft)

            # 更新 Message 狀態為 drafted
            result = await db.execute(
                select(Message).where(Message.id == message_id)
            )
            message = result.scalar_one_or_none()
            if message:
                message.status = "drafted"
                await db.commit()

            print(f"✅ 草稿生成完成 (Message ID: {message_id}, 模式: {complexity})")
            return draft

        except Exception as e:
            # 記錄失敗的 API 調用
            try:
                api_usage = APIUsage(
                    provider="openrouter" if settings.AI_PROVIDER == "openrouter" else "anthropic",
                    model=settings.MODEL_SMART,
                    operation="draft_generation",
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    estimated_cost=0,
                    success=False,
                    error_message=str(e)
                )
                db.add(api_usage)
                await db.commit()
            except:
                pass
            await db.rollback()
            print(f"❌ 草稿生成失敗: {str(e)}")
            raise Exception(f"草稿生成失敗: {str(e)}")

    async def regenerate(
        self,
        db: AsyncSession,
        message_id: int
    ) -> Draft:
        """
        重新生成草稿
        """
        # 取得原始訊息
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            raise ValueError(f"找不到訊息 ID: {message_id}")

        # 生成新草稿
        return await self.generate(
            db=db,
            message_id=message_id,
            content=message.content,
            sender_name=message.sender_name,
            source=message.source
        )


# 全域草稿生成器實例
_draft_generator: Optional[DraftGenerator] = None


def get_draft_generator() -> DraftGenerator:
    """取得草稿生成器單例"""
    global _draft_generator
    if _draft_generator is None:
        _draft_generator = DraftGenerator()
    return _draft_generator
