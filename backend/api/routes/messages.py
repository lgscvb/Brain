"""
Brain - 訊息管理 API 路由
處理訊息 CRUD 與草稿生成
"""
from datetime import datetime
from typing import List
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from sqlalchemy.orm import selectinload
import httpx
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

# CRM API 設定
CRM_API_BASE = "https://auto.yourspce.org/api/db"


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


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """刪除訊息（含相關草稿和回覆）"""
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="訊息不存在")

    # 刪除相關草稿
    await db.execute(
        select(Draft).where(Draft.message_id == message_id)
    )
    drafts = (await db.execute(
        select(Draft).where(Draft.message_id == message_id)
    )).scalars().all()
    for draft in drafts:
        await db.delete(draft)

    # 刪除相關回覆
    responses = (await db.execute(
        select(Response).where(Response.message_id == message_id)
    )).scalars().all()
    for response in responses:
        await db.delete(response)

    # 刪除訊息本身
    await db.delete(message)
    await db.commit()

    return {"success": True, "message": "訊息已刪除"}


@router.delete("/conversations/{sender_id:path}")
async def delete_conversation(
    sender_id: str,
    db: AsyncSession = Depends(get_db)
):
    """刪除整個對話（該客戶所有訊息）"""
    decoded_sender_id = unquote(sender_id)

    # 查詢該客戶所有訊息
    result = await db.execute(
        select(Message).where(Message.sender_id == decoded_sender_id)
    )
    messages = result.scalars().all()

    if not messages:
        raise HTTPException(status_code=404, detail="對話不存在")

    deleted_count = 0
    for message in messages:
        # 刪除相關草稿
        drafts = (await db.execute(
            select(Draft).where(Draft.message_id == message.id)
        )).scalars().all()
        for draft in drafts:
            await db.delete(draft)

        # 刪除相關回覆
        responses = (await db.execute(
            select(Response).where(Response.message_id == message.id)
        )).scalars().all()
        for response in responses:
            await db.delete(response)

        # 刪除訊息
        await db.delete(message)
        deleted_count += 1

    await db.commit()

    return {"success": True, "message": f"已刪除 {deleted_count} 則訊息"}


# ====== 對話列表 API（三欄式佈局用）======

@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db)
):
    """
    取得對話列表（依 sender_id 分組）

    用於三欄式佈局的左欄，顯示所有客戶對話摘要
    """
    # 主查詢：只按 sender_id 分組統計（避免同一用戶因改名而出現重複）
    query = (
        select(
            Message.sender_id,
            func.count(Message.id).label('message_count'),
            func.sum(
                case(
                    (Message.status.in_(['pending', 'drafted']), 1),
                    else_=0
                )
            ).label('unread_count'),
            func.max(Message.created_at).label('last_message_at')
        )
        .group_by(Message.sender_id)
        .order_by(func.max(Message.created_at).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    # 從 CRM 批次取得客戶公司名稱（用 LINE user ID 對應）
    company_name_map = {}
    try:
        # 取得所有 sender_id 對應的 CRM 客戶公司名稱
        sender_ids = [row.sender_id for row in rows]
        if sender_ids:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 取得所有有 LINE UID 的客戶
                response = await client.get(
                    f"{CRM_API_BASE}/customers",
                    params={
                        "select": "line_user_id,company_name",
                        "line_user_id": f"not.is.null",
                        "limit": 500
                    }
                )
                if response.status_code == 200:
                    customers = response.json()
                    company_name_map = {
                        c['line_user_id']: c.get('company_name', '')
                        for c in customers
                        if c.get('line_user_id')
                    }
    except Exception as e:
        print(f"無法取得 CRM 公司名稱: {e}")

    # 取得每個對話的客戶名稱和最後一則訊息（用於預覽）
    conversations = []
    for row in rows:
        # 取得客戶發送的訊息（排除 bot 回覆）來獲取客戶名稱
        customer_msg_result = await db.execute(
            select(Message.sender_name, Message.source)
            .where(Message.sender_id == row.sender_id)
            .where(Message.source.notin_(['line_bot', 'system']))
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        customer_msg = customer_msg_result.one_or_none()

        # 取得最後一則訊息（用於預覽）
        last_msg_result = await db.execute(
            select(Message.content, Message.source)
            .where(Message.sender_id == row.sender_id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        last_msg = last_msg_result.one_or_none()

        preview = ""
        sender_name = "Unknown"
        source = "unknown"

        # 優先使用客戶訊息的名稱
        if customer_msg:
            sender_name = customer_msg.sender_name
            source = customer_msg.source

        if last_msg:
            preview = last_msg.content[:50] + "..." if len(last_msg.content) > 50 else last_msg.content

        # 從 CRM 取得公司名稱
        company_name = company_name_map.get(row.sender_id, "")

        conversations.append({
            "sender_id": row.sender_id,
            "sender_name": sender_name,
            "company_name": company_name,  # 新增：公司名稱
            "source": source,
            "message_count": row.message_count,
            "unread_count": row.unread_count or 0,
            "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None,
            "last_message_preview": preview
        })

    return {"conversations": conversations, "total": len(conversations)}


@router.post("/conversations/{sender_id:path}/generate-draft")
async def generate_conversation_draft(
    sender_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    對話級別草稿生成 - 讀取所有未回覆訊息，生成一個整合回覆

    這是新的「對話導向」模式的核心 API
    """
    decoded_sender_id = unquote(sender_id)
    draft_generator = get_draft_generator()

    try:
        draft = await draft_generator.generate_for_conversation(
            db=db,
            sender_id=decoded_sender_id
        )
        return {
            "success": True,
            "draft": {
                "id": draft.id,
                "content": draft.content,
                "strategy": draft.strategy,
                "intent": draft.intent,
                "message_id": draft.message_id
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"草稿生成失敗: {str(e)}")


@router.post("/conversations/{sender_id:path}/send")
async def send_conversation_reply(
    sender_id: str,
    response_data: ResponseCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    對話級別發送回覆 - 發送後批量更新所有相關訊息狀態

    這是新的「對話導向」模式的發送 API
    """
    decoded_sender_id = unquote(sender_id)

    # 取得該客戶所有未回覆訊息
    result = await db.execute(
        select(Message)
        .where(Message.sender_id == decoded_sender_id)
        .where(Message.status.in_(["pending", "drafted"]))
        .where(Message.source.notin_(["line_bot", "system"]))
        .order_by(desc(Message.created_at))
    )
    pending_messages = result.scalars().all()

    if not pending_messages:
        raise HTTPException(status_code=404, detail="沒有待處理的訊息")

    # 取得最新訊息作為回覆的關聯對象
    latest_message = pending_messages[0]

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

    # 分析修改原因
    modification_reason = None
    if is_modified:
        learning_engine = get_learning_engine()
        modification_reason = await learning_engine.analyze_modification(
            db=db,
            original_draft=original_content,
            final_content=response_data.content
        )

    # 建立回覆記錄（關聯到最新訊息）
    response = Response(
        message_id=latest_message.id,
        draft_id=response_data.draft_id,
        original_content=original_content,
        final_content=response_data.content,
        is_modified=is_modified,
        modification_reason=modification_reason,
        sent_at=datetime.utcnow()
    )
    db.add(response)

    # 批量更新所有相關訊息狀態為 sent
    for msg in pending_messages:
        msg.status = "sent"
        msg.updated_at = datetime.utcnow()

    # 發送 LINE 訊息（如果來源是 LINE）
    if latest_message.source == "line_oa":
        try:
            line_client = get_line_client()
            await line_client.send_text_message(
                user_id=decoded_sender_id,
                text=response_data.content
            )
        except Exception as e:
            print(f"LINE 訊息發送失敗: {str(e)}")

    await db.commit()

    return {
        "success": True,
        "message": f"回覆已發送，{len(pending_messages)} 則訊息已標記為已處理"
    }


@router.get("/conversations/{sender_id:path}/messages")
async def get_conversation_messages(
    sender_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    取得特定客戶的所有訊息（含回覆）

    用於三欄式佈局的中欄，顯示選中客戶的訊息歷史
    """
    # URL decode sender_id (LINE user ID 可能含特殊字元)
    decoded_sender_id = unquote(sender_id)

    # 1. 查詢訊息（含草稿）
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.drafts))
        .where(Message.sender_id == decoded_sender_id)
        .order_by(desc(Message.created_at))
    )
    messages = result.scalars().all()

    # 2. 查詢該客戶所有訊息的回覆
    message_ids = [msg.id for msg in messages]
    response_map = {}
    if message_ids:
        response_result = await db.execute(
            select(Response)
            .where(Response.message_id.in_(message_ids))
        )
        responses = response_result.scalars().all()
        response_map = {r.message_id: r for r in responses}

    # 3. 組合資料（包含回覆資訊）
    messages_data = []
    for msg in messages:
        resp = response_map.get(msg.id)
        msg_dict = {
            "id": msg.id,
            "source": msg.source,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name,
            "content": msg.content,
            "status": msg.status,
            "priority": msg.priority,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "updated_at": msg.updated_at.isoformat() if msg.updated_at else None,
            "drafts": [
                {
                    "id": d.id,
                    "content": d.content,
                    "strategy": d.strategy,
                    "intent": d.intent
                }
                for d in msg.drafts
            ] if msg.drafts else [],
            # 新增：回覆資訊
            "response": {
                "id": resp.id,
                "final_content": resp.final_content,
                "sent_at": resp.sent_at.isoformat() if resp.sent_at else None,
                "is_modified": resp.is_modified
            } if resp else None
        }
        messages_data.append(msg_dict)

    return {"messages": messages_data, "total": len(messages_data)}
