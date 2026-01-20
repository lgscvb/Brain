"""
Brain - 訊息管理 API 路由
處理訊息 CRUD 與草稿生成

【N+1 查詢修復】
- list_conversations: 使用 Window Function 避免迴圈查詢
- delete_message: 使用批量刪除
- delete_conversation: 使用 IN 子句批量刪除

【效能優化】
- CRM 公司名稱快取：5 分鐘 TTL，避免每次請求都呼叫 CRM API
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case, delete
from sqlalchemy.orm import selectinload
import httpx
import time

logger = logging.getLogger(__name__)


# ====== CRM 公司名稱快取 ======
class CompanyNameCache:
    """
    簡單的記憶體快取，用於儲存 CRM 公司名稱

    【設計決策】
    - 使用記憶體快取而非 Redis：Brain 是單一實例部署，不需要分散式快取
    - 5 分鐘 TTL：公司名稱不常變動，但也不能太久
    - 失效時重新載入整個快取：簡化邏輯，避免部分更新問題
    """

    def __init__(self, ttl_seconds: int = 300):  # 預設 5 分鐘
        self._cache: Dict[str, str] = {}
        self._last_update: float = 0
        self._ttl = ttl_seconds

    def is_expired(self) -> bool:
        """檢查快取是否過期"""
        return time.time() - self._last_update > self._ttl

    def get(self, sender_id: str) -> Optional[str]:
        """取得公司名稱（可能為 None 表示不在快取中）"""
        return self._cache.get(sender_id)

    def update(self, data: Dict[str, str]) -> None:
        """更新整個快取"""
        self._cache = data
        self._last_update = time.time()

    def is_empty(self) -> bool:
        """檢查快取是否為空"""
        return len(self._cache) == 0


# 全域快取實例
_company_name_cache = CompanyNameCache(ttl_seconds=300)
from db.database import get_db
from db.models import Message, Draft, Response, Attachment
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
    """取得單一訊息詳情（含草稿和附件）"""
    result = await db.execute(
        select(Message)
        .options(
            selectinload(Message.drafts),
            selectinload(Message.attachments)
        )
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
                logger.error(f"背景草稿生成失敗: {e}")
    
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
            logger.error(f"LINE 訊息發送失敗: {e}")
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
    """
    刪除訊息（含相關草稿和回覆）

    【優化】使用批量刪除，避免 N+1 查詢
    原本：SELECT → 迴圈 DELETE（每個項目一次 DELETE）
    現在：DELETE WHERE（單一語句批量刪除）
    """
    result = await db.execute(
        select(Message).where(Message.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="訊息不存在")

    # 批量刪除相關草稿（單一 DELETE 語句）
    await db.execute(
        delete(Draft).where(Draft.message_id == message_id)
    )

    # 批量刪除相關回覆（單一 DELETE 語句）
    await db.execute(
        delete(Response).where(Response.message_id == message_id)
    )

    # 刪除訊息本身
    await db.delete(message)
    await db.commit()

    return {"success": True, "message": "訊息已刪除"}


@router.delete("/conversations/{sender_id:path}")
async def delete_conversation(
    sender_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    刪除整個對話（該客戶所有訊息）

    【優化】使用 IN 子句批量刪除，避免 N+1 查詢
    原本：對每個訊息執行 2 次 SELECT + 多次 DELETE（N 則訊息 = 3N 次查詢）
    現在：1 次 SELECT 取得 ID + 3 次批量 DELETE = 4 次查詢
    """
    decoded_sender_id = unquote(sender_id)

    # 查詢該客戶所有訊息 ID
    result = await db.execute(
        select(Message.id).where(Message.sender_id == decoded_sender_id)
    )
    message_ids = [row[0] for row in result.all()]

    if not message_ids:
        raise HTTPException(status_code=404, detail="對話不存在")

    # 批量刪除相關草稿（使用 IN 子句）
    await db.execute(
        delete(Draft).where(Draft.message_id.in_(message_ids))
    )

    # 批量刪除相關回覆（使用 IN 子句）
    await db.execute(
        delete(Response).where(Response.message_id.in_(message_ids))
    )

    # 批量刪除所有訊息（使用 IN 子句）
    await db.execute(
        delete(Message).where(Message.id.in_(message_ids))
    )

    await db.commit()

    return {"success": True, "message": f"已刪除 {len(message_ids)} 則訊息"}


# ====== 對話列表 API（三欄式佈局用）======

async def _fetch_crm_company_names(sender_ids: List[str]) -> Dict[str, str]:
    """
    從 CRM 批次取得公司名稱（含快取機制）

    【效能優化】
    - 使用 5 分鐘 TTL 快取
    - 快取命中時直接返回，不呼叫 CRM API
    - 快取未命中或過期時重新載入

    【獨立函數】方便測試和重用
    """
    global _company_name_cache

    if not sender_ids:
        return {}

    # 檢查快取是否有效
    if not _company_name_cache.is_expired() and not _company_name_cache.is_empty():
        # 快取命中，直接返回
        return {sid: _company_name_cache.get(sid) or "" for sid in sender_ids}

    # 快取未命中或過期，重新載入
    company_name_map = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{CRM_API_BASE}/customers",
                params={
                    "select": "line_user_id,company_name",
                    "line_user_id": "not.is.null",
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
                # 更新快取
                _company_name_cache.update(company_name_map)
    except Exception as e:
        logger.warning(f"無法取得 CRM 公司名稱: {e}")
        # API 失敗時，如果有舊快取就用舊快取
        if not _company_name_cache.is_empty():
            return {sid: _company_name_cache.get(sid) or "" for sid in sender_ids}

    return {sid: company_name_map.get(sid, "") for sid in sender_ids}


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db)
):
    """
    取得對話列表（依 sender_id 分組）

    用於三欄式佈局的左欄，顯示所有客戶對話摘要

    【N+1 修復】
    原本：主查詢 + 每個對話 2 次子查詢（N 個對話 = 2N+1 次查詢）
    現在：2 次查詢取得所有資料 + 1 次 CRM API 呼叫
    """
    # ====== 查詢 1：統計資料 ======
    stats_query = (
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
    stats_result = await db.execute(stats_query)
    stats_rows = stats_result.all()

    if not stats_rows:
        return {"conversations": [], "total": 0}

    sender_ids = [row.sender_id for row in stats_rows]

    # ====== 查詢 2：批次取得每個 sender 的最新訊息資訊 ======
    # 使用子查詢找出每個 sender 的最新訊息 ID
    latest_msg_subquery = (
        select(
            Message.sender_id,
            func.max(Message.id).label('latest_id')
        )
        .where(Message.sender_id.in_(sender_ids))
        .group_by(Message.sender_id)
        .subquery()
    )

    # 取得最新訊息的詳細資料
    latest_msgs_query = (
        select(
            Message.sender_id,
            Message.sender_name,
            Message.source,
            Message.content
        )
        .join(
            latest_msg_subquery,
            (Message.sender_id == latest_msg_subquery.c.sender_id) &
            (Message.id == latest_msg_subquery.c.latest_id)
        )
    )
    latest_msgs_result = await db.execute(latest_msgs_query)
    latest_msgs = {row.sender_id: row for row in latest_msgs_result.all()}

    # ====== 外部 API：批次取得 CRM 公司名稱 ======
    company_name_map = await _fetch_crm_company_names(sender_ids)

    # ====== 組合結果 ======
    conversations = []
    for row in stats_rows:
        latest_msg = latest_msgs.get(row.sender_id)

        sender_name = "Unknown"
        source = "unknown"
        preview = ""

        if latest_msg:
            sender_name = latest_msg.sender_name or "Unknown"
            source = latest_msg.source or "unknown"
            content = latest_msg.content or ""
            preview = content[:50] + "..." if len(content) > 50 else content

        company_name = company_name_map.get(row.sender_id, "")

        conversations.append({
            "sender_id": row.sender_id,
            "sender_name": sender_name,
            "company_name": company_name,
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
            logger.error(f"LINE 訊息發送失敗: {e}")

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

    # 1. 查詢訊息（含草稿和附件）
    result = await db.execute(
        select(Message)
        .options(
            selectinload(Message.drafts),
            selectinload(Message.attachments)
        )
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
            } if resp else None,
            # 新增：附件資訊（圖片、PDF 等媒體檔案）
            "attachments": [
                {
                    "id": att.id,
                    "media_type": att.media_type,
                    "file_name": att.file_name,
                    "file_size": att.file_size,
                    "r2_url": att.r2_url,
                    "ocr_text": att.ocr_text[:200] + "..." if att.ocr_text and len(att.ocr_text) > 200 else att.ocr_text,
                    "ocr_status": att.ocr_status,
                    "created_at": att.created_at.isoformat() if att.created_at else None
                }
                for att in msg.attachments
            ] if msg.attachments else []
        }
        messages_data.append(msg_dict)

    return {"messages": messages_data, "total": len(messages_data)}
