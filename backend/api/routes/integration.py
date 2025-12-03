"""
Brain - 整合 API
提供給 Jungle CRM 調用的 API 端點
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from db.database import get_db
from db.models import Message, Draft, Response

router = APIRouter(prefix="/api/integration", tags=["integration"])


# === Pydantic Models ===

class ConversationMessage(BaseModel):
    """對話訊息"""
    id: int
    content: str
    sender_id: str
    sender_name: str
    source: str
    status: str
    created_at: str
    draft: Optional[dict] = None
    response: Optional[dict] = None


class ConversationListResponse(BaseModel):
    """對話列表回應"""
    items: List[ConversationMessage]
    total: int
    page: int
    page_size: int


class ConversationStats(BaseModel):
    """對話統計"""
    total_messages: int
    total_responses: int
    ai_adoption_rate: float  # AI 採用率（未修改直接發送的比例）
    last_interaction: Optional[str] = None
    first_interaction: Optional[str] = None


# === API 端點 ===

@router.get("/conversations/{line_user_id}", response_model=ConversationListResponse)
async def get_conversations(
    line_user_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    取得特定 LINE 用戶的對話歷史

    - **line_user_id**: LINE 用戶 ID (sender_id)
    - **page**: 頁碼（從 1 開始）
    - **page_size**: 每頁筆數（最多 100）
    - **start_date**: 開始日期 (YYYY-MM-DD)
    - **end_date**: 結束日期 (YYYY-MM-DD)
    """
    # 建立基礎查詢
    query = select(Message).where(Message.sender_id == line_user_id)

    # 日期篩選
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where(Message.created_at >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式錯誤，請使用 YYYY-MM-DD")

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.where(Message.created_at < end)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式錯誤，請使用 YYYY-MM-DD")

    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分頁查詢
    offset = (page - 1) * page_size
    query = query.order_by(desc(Message.created_at)).offset(offset).limit(page_size)

    result = await db.execute(query)
    messages = result.scalars().all()

    # 組裝回應
    items = []
    for msg in messages:
        # 取得草稿
        draft_result = await db.execute(
            select(Draft).where(Draft.message_id == msg.id).order_by(desc(Draft.created_at)).limit(1)
        )
        draft = draft_result.scalar_one_or_none()

        # 取得回覆
        response_result = await db.execute(
            select(Response).where(Response.message_id == msg.id).order_by(desc(Response.sent_at)).limit(1)
        )
        response = response_result.scalar_one_or_none()

        items.append(ConversationMessage(
            id=msg.id,
            content=msg.content,
            sender_id=msg.sender_id,
            sender_name=msg.sender_name,
            source=msg.source,
            status=msg.status,
            created_at=msg.created_at.isoformat() if msg.created_at else "",
            draft={
                "id": draft.id,
                "content": draft.content,
                "intent": draft.intent,
                "strategy": draft.strategy
            } if draft else None,
            response={
                "id": response.id,
                "original_content": response.original_content,
                "final_content": response.final_content,
                "is_modified": response.is_modified,
                "sent_at": response.sent_at.isoformat() if response.sent_at else ""
            } if response else None
        ))

    return ConversationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/conversations/{line_user_id}/stats", response_model=ConversationStats)
async def get_conversation_stats(
    line_user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    取得特定 LINE 用戶的對話統計

    - **line_user_id**: LINE 用戶 ID (sender_id)

    回傳：
    - total_messages: 總訊息數
    - total_responses: 總回覆數
    - ai_adoption_rate: AI 採用率（未修改直接發送的比例）
    - last_interaction: 最後互動時間
    - first_interaction: 首次互動時間
    """
    # 總訊息數
    msg_count_result = await db.execute(
        select(func.count()).select_from(Message).where(Message.sender_id == line_user_id)
    )
    total_messages = msg_count_result.scalar() or 0

    # 總回覆數和 AI 採用率
    response_result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(func.cast(Response.is_modified == False, type_=int)).label("unmodified")
        ).select_from(Response)
        .join(Message, Message.id == Response.message_id)
        .where(Message.sender_id == line_user_id)
    )
    response_stats = response_result.first()
    total_responses = response_stats.total or 0
    unmodified = response_stats.unmodified or 0

    ai_adoption_rate = (unmodified / total_responses * 100) if total_responses > 0 else 0

    # 最後/首次互動時間
    time_result = await db.execute(
        select(
            func.max(Message.created_at).label("last"),
            func.min(Message.created_at).label("first")
        ).where(Message.sender_id == line_user_id)
    )
    time_stats = time_result.first()

    return ConversationStats(
        total_messages=total_messages,
        total_responses=total_responses,
        ai_adoption_rate=round(ai_adoption_rate, 2),
        last_interaction=time_stats.last.isoformat() if time_stats.last else None,
        first_interaction=time_stats.first.isoformat() if time_stats.first else None
    )


@router.get("/health")
async def integration_health():
    """整合 API 健康檢查"""
    return {
        "status": "ok",
        "service": "brain-integration-api",
        "timestamp": datetime.now().isoformat()
    }
