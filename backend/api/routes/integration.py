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


class ExternalMessageLog(BaseModel):
    """外部系統訊息記錄"""
    sender_id: str  # LINE User ID
    sender_name: str
    content: str  # 訊息內容或操作描述
    message_type: str = "bot_reply"  # bot_reply, user_action, system_event
    source: str = "mcp_server"  # 來源系統
    timestamp: Optional[str] = None  # ISO 格式時間戳（重要！確保對話順序正確）
    metadata: Optional[dict] = None  # 額外資訊（如選單選項、預約詳情等）


class ExternalMessageLogResponse(BaseModel):
    """記錄回應"""
    success: bool
    message_id: Optional[int] = None
    error: Optional[str] = None


@router.post("/log", response_model=ExternalMessageLogResponse)
async def log_external_message(
    log_data: ExternalMessageLog,
    db: AsyncSession = Depends(get_db)
):
    """
    記錄外部系統的訊息（供 MCP Server 呼叫）

    用途：
    - 記錄 LINE Bot 發送給用戶的訊息
    - 記錄用戶在選單上的操作
    - 讓 Brain 能看到完整的對話上下文

    message_type 說明：
    - bot_reply: Bot 發送給用戶的訊息
    - user_action: 用戶的選單操作（如選擇日期、選擇時段）
    - system_event: 系統事件（如預約成功、取消預約）
    """
    try:
        # 解析時間戳（如果有提供）
        created_at = None
        if log_data.timestamp:
            try:
                # 支援多種時間格式
                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        created_at = datetime.strptime(log_data.timestamp, fmt)
                        break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"⚠️ 時間戳解析失敗: {log_data.timestamp}, 使用當前時間")
                created_at = None

        # 根據 message_type 決定如何記錄
        if log_data.message_type == "bot_reply":
            # Bot 回覆：記錄到 messages 表，source 為 "line_bot"
            message = Message(
                source="line_bot",
                sender_id=log_data.sender_id,
                sender_name="Hour Jungle Bot",  # Bot 名稱
                content=log_data.content,
                status="sent",
                priority="low"
            )
        elif log_data.message_type == "user_action":
            # 用戶操作：記錄到 messages 表，標記為用戶行為
            message = Message(
                source="line_oa",
                sender_id=log_data.sender_id,
                sender_name=log_data.sender_name,
                content=f"[操作] {log_data.content}",
                status="action",  # 特殊狀態表示這是操作記錄
                priority="low"
            )
        else:  # system_event
            # 系統事件：記錄到 messages 表
            message = Message(
                source="system",
                sender_id=log_data.sender_id,
                sender_name="System",
                content=f"[系統] {log_data.content}",
                status="event",
                priority="low"
            )

        # 如果有提供時間戳，覆蓋默認的 created_at
        if created_at:
            message.created_at = created_at

        db.add(message)
        await db.commit()
        await db.refresh(message)

        print(f"📝 [Integration] 記錄外部訊息: {log_data.message_type} - {log_data.content[:50]}...")

        return ExternalMessageLogResponse(
            success=True,
            message_id=message.id
        )

    except Exception as e:
        print(f"❌ [Integration] 記錄失敗: {str(e)}")
        return ExternalMessageLogResponse(
            success=False,
            error=str(e)
        )


@router.get("/health")
async def integration_health():
    """整合 API 健康檢查"""
    return {
        "status": "ok",
        "service": "brain-integration-api",
        "timestamp": datetime.now().isoformat()
    }
