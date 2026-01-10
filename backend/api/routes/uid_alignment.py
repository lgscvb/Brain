"""
Brain - UID 對齊 API
用於將 LINE User ID 與 CRM 客戶進行手動配對
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, desc
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import httpx

from db.database import get_db
from db.models import Message

router = APIRouter(prefix="/api/uid-alignment", tags=["uid-alignment"])

# CRM API 端點
CRM_API_BASE = "https://auto.yourspce.org/api/db"


# === Pydantic Models ===

class UnmatchedSender(BaseModel):
    """未匹配的發送者"""
    sender_id: str
    sender_name: str
    message_count: int
    first_message_at: str
    last_message_at: str
    last_message_preview: Optional[str] = None


class UnmatchedListResponse(BaseModel):
    """未匹配列表回應"""
    items: List[UnmatchedSender]
    total: int


class CrmCustomer(BaseModel):
    """CRM 客戶"""
    id: int
    legacy_id: Optional[str] = None
    name: str
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    line_user_id: Optional[str] = None
    status: Optional[str] = None


class CustomersWithoutUidResponse(BaseModel):
    """無 LINE UID 的客戶列表"""
    items: List[CrmCustomer]
    total: int


class LinkUidRequest(BaseModel):
    """連結 UID 請求"""
    customer_id: int
    line_user_id: str


class LinkUidResponse(BaseModel):
    """連結 UID 回應"""
    success: bool
    message: str
    customer_id: int
    line_user_id: str


# === API 端點 ===

@router.get("/unmatched-senders", response_model=UnmatchedListResponse)
async def get_unmatched_senders(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    取得所有未匹配的 LINE 發送者

    這些是在 Brain 收到訊息但尚未與 CRM 客戶關聯的 LINE 用戶
    """
    # 先從 CRM 取得所有已有 LINE UID 的客戶
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{CRM_API_BASE}/customers",
                params={
                    "select": "line_user_id",
                    "line_user_id": "not.is.null",
                    "limit": 1000
                }
            )
            crm_customers = response.json()
            matched_uids = set(c['line_user_id'] for c in crm_customers if c.get('line_user_id'))
    except Exception as e:
        print(f"無法連接 CRM API: {e}")
        matched_uids = set()

    # 查詢 Brain 中所有唯一的 sender_id
    query = select(
        Message.sender_id,
        Message.sender_name,
        func.count(Message.id).label('message_count'),
        func.min(Message.created_at).label('first_message_at'),
        func.max(Message.created_at).label('last_message_at')
    ).group_by(
        Message.sender_id, Message.sender_name
    ).order_by(desc('last_message_at'))

    result = await db.execute(query)
    all_senders = result.all()

    # 過濾出未匹配的
    items = []
    for sender in all_senders:
        if sender.sender_id not in matched_uids:
            # 如果有搜尋條件，進行過濾
            if search:
                search_lower = search.lower()
                if (search_lower not in (sender.sender_name or '').lower() and
                    search_lower not in (sender.sender_id or '').lower()):
                    continue

            # 取得最後一則訊息預覽
            last_msg_result = await db.execute(
                select(Message.content)
                .where(Message.sender_id == sender.sender_id)
                .order_by(desc(Message.created_at))
                .limit(1)
            )
            last_msg = last_msg_result.scalar()

            items.append(UnmatchedSender(
                sender_id=sender.sender_id,
                sender_name=sender.sender_name or '未知用戶',
                message_count=sender.message_count,
                first_message_at=sender.first_message_at.isoformat() if sender.first_message_at else '',
                last_message_at=sender.last_message_at.isoformat() if sender.last_message_at else '',
                last_message_preview=last_msg[:100] if last_msg else None
            ))

    return UnmatchedListResponse(
        items=items,
        total=len(items)
    )


@router.get("/customers-without-uid", response_model=CustomersWithoutUidResponse)
async def get_customers_without_uid(
    search: Optional[str] = None,
    status: str = "active",
    has_contract: bool = True
):
    """
    取得所有沒有 LINE User ID 的 CRM 客戶

    Args:
        search: 搜尋關鍵字
        status: 客戶狀態 (active/all)
        has_contract: 是否只顯示有活躍合約的客戶 (預設 True)
    """
    try:
        # 1. 先取得有活躍合約的客戶 ID 列表
        active_contract_customer_ids = set()
        if has_contract:
            async with httpx.AsyncClient(timeout=10.0) as client:
                contracts_response = await client.get(
                    f"{CRM_API_BASE}/contracts",
                    params={
                        "select": "customer_id",
                        "status": "eq.active",
                        "limit": 2000
                    }
                )
                contracts = contracts_response.json()
                active_contract_customer_ids = set(c['customer_id'] for c in contracts if c.get('customer_id'))

        # 2. 取得沒有 LINE UID 的客戶
        params = {
            "select": "id,legacy_id,name,company_name,phone,email,line_user_id,status",
            "line_user_id": "is.null",
            "limit": 500,
            "order": "legacy_id.asc"
        }

        if status and status != "all":
            params["status"] = f"eq.{status}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CRM_API_BASE}/customers", params=params)
            customers = response.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"無法連接 CRM API: {str(e)}")

    # 3. 過濾：只保留有活躍合約的客戶
    if has_contract and active_contract_customer_ids:
        customers = [c for c in customers if c.get('id') in active_contract_customer_ids]

    # 4. 過濾搜尋
    if search:
        search_lower = search.lower()
        customers = [
            c for c in customers
            if (search_lower in (c.get('name') or '').lower() or
                search_lower in (c.get('company_name') or '').lower() or
                search_lower in (c.get('legacy_id') or '').lower() or
                search_lower in (c.get('phone') or '').lower())
        ]

    items = [CrmCustomer(**c) for c in customers]

    return CustomersWithoutUidResponse(
        items=items,
        total=len(items)
    )


@router.post("/link", response_model=LinkUidResponse)
async def link_uid(request: LinkUidRequest):
    """
    將 LINE User ID 連結到 CRM 客戶
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 更新客戶的 LINE User ID
            response = await client.patch(
                f"{CRM_API_BASE}/customers",
                params={"id": f"eq.{request.customer_id}"},
                json={"line_user_id": request.line_user_id},
                headers={"Prefer": "return=representation"}
            )

            if response.status_code == 200:
                updated = response.json()
                if updated:
                    return LinkUidResponse(
                        success=True,
                        message=f"成功將 LINE UID 連結到客戶 {updated[0].get('name', '')}",
                        customer_id=request.customer_id,
                        line_user_id=request.line_user_id
                    )

            raise HTTPException(status_code=400, detail="更新失敗")

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"無法連接 CRM API: {str(e)}")


@router.delete("/link/{customer_id}", response_model=LinkUidResponse)
async def unlink_uid(customer_id: int):
    """
    移除客戶的 LINE User ID 連結
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 清空客戶的 LINE User ID
            response = await client.patch(
                f"{CRM_API_BASE}/customers",
                params={"id": f"eq.{customer_id}"},
                json={"line_user_id": None},
                headers={"Prefer": "return=representation"}
            )

            if response.status_code == 200:
                updated = response.json()
                if updated:
                    return LinkUidResponse(
                        success=True,
                        message=f"已移除客戶 {updated[0].get('name', '')} 的 LINE UID 連結",
                        customer_id=customer_id,
                        line_user_id=""
                    )

            raise HTTPException(status_code=400, detail="更新失敗")

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"無法連接 CRM API: {str(e)}")


@router.get("/stats")
async def get_alignment_stats(db: AsyncSession = Depends(get_db)):
    """
    取得 UID 對齊統計（只計算有活躍合約的客戶）
    """
    # Brain 中唯一發送者數
    brain_result = await db.execute(
        select(func.count(distinct(Message.sender_id)))
    )
    brain_unique_senders = brain_result.scalar() or 0

    # CRM 客戶統計（只計算有活躍合約的客戶）
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. 先取得有活躍合約的客戶 ID 列表
            contracts_response = await client.get(
                f"{CRM_API_BASE}/contracts",
                params={
                    "select": "customer_id",
                    "status": "eq.active",
                    "limit": 2000
                }
            )
            contracts = contracts_response.json()
            active_contract_customer_ids = set(c['customer_id'] for c in contracts if c.get('customer_id'))

            # 2. 取得這些客戶的詳細資料
            customers_response = await client.get(
                f"{CRM_API_BASE}/customers",
                params={
                    "select": "id,line_user_id",
                    "status": "eq.active",
                    "limit": 2000
                }
            )
            all_customers = customers_response.json()

            # 3. 只計算有活躍合約的客戶
            customers_with_contract = [c for c in all_customers if c.get('id') in active_contract_customer_ids]
            total_customers = len(customers_with_contract)
            with_uid = len([c for c in customers_with_contract if c.get('line_user_id')])

    except Exception as e:
        print(f"無法取得 CRM 統計: {e}")
        total_customers = 0
        with_uid = 0

    return {
        "brain_unique_senders": brain_unique_senders,
        "crm_total_customers": total_customers,
        "crm_with_line_uid": with_uid,
        "crm_without_line_uid": total_customers - with_uid,
        "alignment_rate": round((with_uid / total_customers * 100) if total_customers > 0 else 0, 1)
    }
