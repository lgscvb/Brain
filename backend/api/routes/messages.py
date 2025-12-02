"""
Brain - 訊息管理 API 路由
處理訊息 CRUD 與草稿生成
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from db.database import get_db
from db.models import Message, Draft, Response
from db.schemas import (
    MessageCreate,
    MessageRead,
    MessageSimple,
    MessageList,
    ResponseCreate,
)
from brain.draft_generator import get_draft_generator
from brain.learning import get_learning_engine
from services.line_client import get_line_client


router = APIRouter()


@router.get("/messages", response_model=MessageList)
async def get_messages(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    取得訊息列表
    
    Args:
        status: 篩選狀態 (pending, drafted, sent, archived)
        limit: 每頁筆數
        offset: 偏移量
    """
    query = select(Message)
    
    if status:
        query = query.where(Message.status == status)
    
    query = query.order_by(desc(Message.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # 計算總數
    count_query = select(func.count(Message.id))
    if status:
        count_query = count_query.where(Message.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return MessageList(messages=messages, total=total)


@router.get("/messages/pending", response_model=MessageList)
async def get_pending_messages(
    db: AsyncSession = Depends(get_db)
):
    """取得待處理訊息（包含草稿）"""
    result = await db.execute(
        select(Message)
        .where(Message.status.in_(["pending", "drafted"]))
        .order_by(desc(Message.priority), desc(Message.created_at))
    )
    messages = result.scalars().all()
    
    return MessageList(messages=messages, total=len(messages))


@router.get("/messages/{message_id}", response_model=MessageRead)
async def get_message(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """取得單一訊息詳情"""
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.drafts))
        .where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="訊息不存在")
    
    return message


@router.post("/messages", response_model=MessageSimple)
async def create_message(
    message_data: MessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    建立新訊息（手動輸入）
    
    建立後會自動在背景生成草稿
    """
    # 建立訊息
    message = Message(
        source=message_data.source,
        sender_id=message_data.sender_id,
        sender_name=message_data.sender_name,
        content=message_data.content,
        priority=message_data.priority or "medium",
        status="pending"
    )
    
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    # 背景生成草稿（使用獨立 Session）
    async def generate_draft_task():
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as task_db:
            draft_generator = get_draft_generator()
            try:
                await draft_generator.generate(
                    db=task_db,
                    message_id=message.id,
                    content=message.content,
                    sender_name=message.sender_name,
                    source=message.source,
                    sender_id=message.sender_id  # 用於取得對話歷史
                )
            except Exception as e:
                print(f"背景草稿生成失敗: {str(e)}")
    
    background_tasks.add_task(generate_draft_task)
    
    return message


@router.post("/messages/{message_id}/send")
async def send_reply(
    message_id: int,
    response_data: ResponseCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    發送回覆
    
    Args:
        message_id: 訊息 ID
        response_data: 回覆內容（可能已修改）
    """
    # 取得訊息
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="訊息不存在")
    
    # 取得原始草稿（如果有）
    original_content = None
    if response_data.draft_id:
        draft_result = await db.execute(
            select(Draft).where(Draft.id == response_data.draft_id)
        )
        draft = draft_result.scalar_one_or_none()
        if draft:
            original_content = draft.content
    
    # 判斷是否修改
    is_modified = (
        original_content is not None and
        original_content.strip() != response_data.content.strip()
    )
    
    # 分析修改原因（如果有修改）
    modification_reason = None
    if is_modified:
        learning_engine = get_learning_engine()
        modification_reason = await learning_engine.analyze_modification(
            db=db,
            original_draft=original_content,
            final_content=response_data.content
        )
    
    # 建立回覆記錄
    response = Response(
        message_id=message_id,
        draft_id=response_data.draft_id,
        original_content=original_content,
        final_content=response_data.content,
        is_modified=is_modified,
        modification_reason=modification_reason,
        sent_at=datetime.utcnow()
    )
    
    db.add(response)
    
    # 更新訊息狀態
    message.status = "sent"
    message.updated_at = datetime.utcnow()
    
    # 發送 LINE 訊息（如果來源是 LINE）
    if message.source == "line_oa":
        try:
            line_client = get_line_client()
            await line_client.send_text_message(
                user_id=message.sender_id,
                text=response_data.content
            )
        except Exception as e:
            print(f"LINE 訊息發送失敗: {str(e)}")
            # 不中斷流程，但記錄錯誤
    
    await db.commit()
    
    return {"success": True, "message": "回覆已發送"}


@router.post("/messages/{message_id}/regenerate")
async def regenerate_draft(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """重新生成草稿"""
    draft_generator = get_draft_generator()
    
    try:
        draft = await draft_generator.regenerate(
            db=db,
            message_id=message_id
        )
        return {"success": True, "draft_id": draft.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"草稿生成失敗: {str(e)}")


@router.post("/messages/{message_id}/archive")
async def archive_message(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """標記訊息為已處理（不發送）"""
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="訊息不存在")
    
    message.status = "archived"
    message.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "訊息已封存"}
