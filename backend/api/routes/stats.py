"""
Brain - 統計資料 API 路由
提供系統統計與學習記錄
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.database import get_db
from db.models import Message, Response
from db.schemas import StatsRead
from brain.learning import get_learning_engine


router = APIRouter()


@router.get("/stats", response_model=StatsRead)
async def get_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    取得系統統計資料
    
    Returns:
        {
            "pending_count": 待處理數量,
            "today_sent": 今日已發送數量,
            "modification_rate": 修改率（%）,
            "avg_response_time": 平均回覆時間（秒）
        }
    """
    # 待處理數量
    pending_result = await db.execute(
        select(func.count(Message.id))
        .where(Message.status.in_(["pending", "drafted"]))
    )
    pending_count = pending_result.scalar() or 0
    
    # 今日已發送數量
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(Response.id))
        .where(Response.sent_at >= today_start)
    )
    today_sent = today_result.scalar() or 0
    
    # 修改率
    learning_engine = get_learning_engine()
    modification_rate = await learning_engine.calculate_modification_rate(db)
    
    # 平均回覆時間（簡化版：計算從訊息建立到發送的平均時間）
    # TODO: 需要更精確的計算邏輯
    avg_response_time = None
    
    return StatsRead(
        pending_count=pending_count,
        today_sent=today_sent,
        modification_rate=modification_rate,
        avg_response_time=avg_response_time
    )


@router.get("/learning/recent")
async def get_recent_learning(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    取得最近的學習記錄
    
    Args:
        limit: 回傳筆數
    
    Returns:
        最近的修改記錄列表
    """
    learning_engine = get_learning_engine()
    modifications = await learning_engine.get_recent_modifications(
        db=db,
        limit=limit
    )
    
    return {
        "modifications": modifications,
        "total": len(modifications)
    }
