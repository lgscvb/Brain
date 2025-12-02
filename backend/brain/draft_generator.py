"""
Brain - 草稿生成器
整合意圖分類與 Claude API 生成回覆草稿
"""
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Message, Draft, APIUsage
from services.claude_client import get_claude_client
from brain.router import get_intent_router
from api.routes.usage import calculate_cost


class DraftGenerator:
    """草稿生成器"""
    
    def __init__(self):
        """初始化草稿生成器"""
        self.claude_client = get_claude_client()
        self.intent_router = get_intent_router()
    
    async def generate(
        self,
        db: AsyncSession,
        message_id: int,
        content: str,
        sender_name: str,
        source: str
    ) -> Draft:
        """
        生成草稿
        
        Args:
            db: 資料庫 Session
            message_id: 訊息 ID
            content: 訊息內容
            sender_name: 發送者名稱
            source: 訊息來源
        
        Returns:
            Draft 物件
        """
        try:
            # 1. 意圖分類
            intent_result = self.intent_router.classify_intent(content)
            intent = intent_result["intent"]
            
            # 2. 呼叫 Claude API 生成草稿
            draft_result = await self.claude_client.generate_draft(
                message=content,
                sender_name=sender_name,
                source=source,
                context={"intent": intent_result}
            )

            # 2.5 記錄 API 用量
            usage_info = draft_result.pop("_usage", None)
            if usage_info:
                api_usage = APIUsage(
                    provider="anthropic",
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

            # 3. 建立 Draft 記錄
            draft = Draft(
                message_id=message_id,
                content=draft_result.get("draft", ""),
                strategy=draft_result.get("strategy", ""),
                intent=draft_result.get("intent", intent),
                is_selected=False
            )

            db.add(draft)
            await db.commit()
            await db.refresh(draft)

            # 4. 更新 Message 狀態為 drafted
            result = await db.execute(
                select(Message).where(Message.id == message_id)
            )
            message = result.scalar_one_or_none()
            if message:
                message.status = "drafted"
                await db.commit()

            return draft

        except Exception as e:
            # 記錄失敗的 API 調用
            try:
                api_usage = APIUsage(
                    provider="anthropic",
                    model=self.claude_client.model,
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
            raise Exception(f"草稿生成失敗: {str(e)}")
    
    async def regenerate(
        self,
        db: AsyncSession,
        message_id: int
    ) -> Draft:
        """
        重新生成草稿
        
        Args:
            db: 資料庫 Session
            message_id: 訊息 ID
        
        Returns:
            新的 Draft 物件
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
