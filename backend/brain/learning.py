"""
Brain - 學習引擎
分析人工修改模式，持續優化 AI

【型別提示說明】
- ModificationRecord: 修改記錄（id, original_content, final_content, ...）

【用途】
1. 分析人工對 AI 草稿的修改原因
2. 統計修改率，衡量 AI 品質
3. 作為未來 Fine-tuning 的資料來源
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from db.models import Response
from services.claude_client import get_claude_client
from type_defs import ModificationRecord


class LearningEngine:
    """學習引擎"""
    
    def __init__(self):
        """初始化學習引擎"""
        self.claude_client = get_claude_client()
    
    async def analyze_modification(
        self,
        db: AsyncSession,
        original_draft: str,
        final_content: str
    ) -> str:
        """
        分析人工修改原因
        
        Args:
            db: 資料庫 Session
            original_draft: AI 原始草稿
            final_content: 人工修改後的內容
        
        Returns:
            修改原因分析
        """
        # 判斷是否有修改
        if original_draft.strip() == final_content.strip():
            return "內容未修改"
        
        # 使用 Claude 分析修改原因
        try:
            reason = await self.claude_client.analyze_modification(
                original=original_draft,
                final=final_content
            )
            return reason
        except Exception as e:
            return f"分析失敗: {str(e)}"
    
    async def get_recent_modifications(
        self,
        db: AsyncSession,
        limit: int = 10
    ) -> List[ModificationRecord]:
        """
        取得最近的修改記錄

        Args:
            db: 資料庫 Session
            limit: 回傳筆數（預設 10 筆）

        Returns:
            List[ModificationRecord]: 修改記錄列表，按發送時間倒序
        """
        result = await db.execute(
            select(Response)
            .where(Response.is_modified == True)
            .order_by(desc(Response.sent_at))
            .limit(limit)
        )
        responses = result.scalars().all()
        
        modifications: List[ModificationRecord] = []
        for response in responses:
            record: ModificationRecord = {
                "id": response.id,
                "original_content": response.original_content or "",
                "final_content": response.final_content or "",
                "modification_reason": response.modification_reason,
                "sent_at": response.sent_at.isoformat() if response.sent_at else "",
            }
            modifications.append(record)

        return modifications
    
    async def calculate_modification_rate(
        self,
        db: AsyncSession
    ) -> float:
        """
        計算修改率
        
        Args:
            db: 資料庫 Session
        
        Returns:
            修改率（0-100）
        """
        # 總回覆數
        total_result = await db.execute(
            select(Response)
        )
        total = len(total_result.scalars().all())
        
        if total == 0:
            return 0.0
        
        # 修改數
        modified_result = await db.execute(
            select(Response).where(Response.is_modified == True)
        )
        modified = len(modified_result.scalars().all())
        
        return (modified / total) * 100


# 全域學習引擎實例
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    """取得學習引擎單例"""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine
