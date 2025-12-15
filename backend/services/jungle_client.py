"""
Brain - Hour Jungle CRM API 客戶端
連接新的 PostgreSQL + PostgREST CRM 系統
"""
import httpx
from typing import Optional, Dict, Any, List
from config import settings


class JungleClient:
    """Hour Jungle CRM API 客戶端 (PostgREST)"""

    def __init__(self):
        """初始化客戶端"""
        # 優先使用 CRM_API_URL，否則使用 JUNGLE_API_URL（向後相容）
        self.base_url = settings.CRM_API_URL or settings.JUNGLE_API_URL
        self.enabled = settings.ENABLE_JUNGLE_INTEGRATION
        self.timeout = 10.0  # 秒

        if self.enabled:
            print(f"🔗 JungleClient 初始化: base_url={self.base_url}")

    def _get_headers(self) -> Dict[str, str]:
        """取得請求標頭"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_customer_by_line_id(self, line_user_id: str) -> Optional[Dict[str, Any]]:
        """
        透過 LINE userId 查詢客戶資料

        Args:
            line_user_id: LINE 用戶 ID

        Returns:
            客戶資料字典，如果找不到則返回 None
        """
        if not self.enabled or not self.base_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 查詢客戶
                response = await client.get(
                    f"{self.base_url}/api/db/customers",
                    headers=self._get_headers(),
                    params={"line_user_id": f"eq.{line_user_id}", "limit": 1}
                )

                if response.status_code == 200:
                    customers = response.json()
                    if not customers:
                        return None

                    customer = customers[0]
                    customer_id = customer.get("id")

                    # 查詢合約
                    contracts = await self._get_contracts(client, customer_id)

                    # 計算繳費狀態
                    payment_status = await self._get_payment_status(client, customer_id)

                    return {
                        "id": customer.get("id"),
                        "name": customer.get("name"),
                        "phone": customer.get("phone"),
                        "email": customer.get("email"),
                        "company_name": customer.get("company_name"),
                        "line_id": customer.get("line_user_id"),
                        "contracts": contracts,
                        "payment_status": payment_status,
                        "created_at": customer.get("created_at"),
                    }
                else:
                    print(f"⚠️ CRM API 錯誤: {response.status_code}")
                    return None

        except httpx.TimeoutException:
            print(f"⚠️ CRM API 超時")
            return None
        except Exception as e:
            print(f"⚠️ CRM API 連線失敗: {e}")
            return None

    async def _get_contracts(self, client: httpx.AsyncClient, customer_id: int) -> List[Dict[str, Any]]:
        """取得客戶的合約"""
        try:
            response = await client.get(
                f"{self.base_url}/api/db/contracts",
                headers=self._get_headers(),
                params={
                    "customer_id": f"eq.{customer_id}",
                    "order": "created_at.desc",
                    "limit": 10
                }
            )

            if response.status_code == 200:
                contracts = response.json()
                return [
                    {
                        "id": c.get("id"),
                        "project_name": c.get("plan_name") or c.get("contract_type"),
                        "contract_type": c.get("contract_type"),
                        "start_day": c.get("start_date"),
                        "end_day": c.get("end_date"),
                        "status": "active" if c.get("status") == "active" else "inactive",
                        "contract_status": c.get("status"),
                        "next_pay_day": None,  # 從 payments 計算
                        "current_payment": c.get("monthly_rent"),
                    }
                    for c in contracts
                ]
            return []
        except Exception as e:
            print(f"⚠️ 查詢合約失敗: {e}")
            return []

    async def _get_payment_status(self, client: httpx.AsyncClient, customer_id: int) -> Dict[str, Any]:
        """計算繳費狀態"""
        try:
            # 查詢待繳款項
            response = await client.get(
                f"{self.base_url}/api/db/payments",
                headers=self._get_headers(),
                params={
                    "customer_id": f"eq.{customer_id}",
                    "payment_status": "eq.pending",
                    "order": "due_date.asc",
                    "limit": 5
                }
            )

            if response.status_code == 200:
                pending_payments = response.json()

                if pending_payments:
                    # 檢查是否逾期
                    from datetime import date
                    today = date.today().isoformat()

                    overdue = [p for p in pending_payments if p.get("due_date", "") < today]
                    upcoming = [p for p in pending_payments if p.get("due_date", "") >= today]

                    if overdue:
                        total_overdue = sum(float(p.get("amount", 0)) for p in overdue)
                        return {
                            "overdue": True,
                            "overdue_count": len(overdue),
                            "overdue_amount": total_overdue,
                        }
                    elif upcoming:
                        return {
                            "overdue": False,
                            "upcoming": True,
                            "upcoming_date": upcoming[0].get("due_date"),
                            "upcoming_amount": float(upcoming[0].get("amount", 0)),
                        }

            return {"overdue": False, "upcoming": False}

        except Exception as e:
            print(f"⚠️ 查詢繳費狀態失敗: {e}")
            return {"overdue": False, "upcoming": False}

    async def get_customer_contracts(self, line_user_id: str) -> List[Dict[str, Any]]:
        """
        查詢客戶的所有合約

        Args:
            line_user_id: LINE 用戶 ID

        Returns:
            合約列表
        """
        if not self.enabled or not self.base_url:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 先查客戶 ID
                response = await client.get(
                    f"{self.base_url}/api/db/customers",
                    headers=self._get_headers(),
                    params={"line_user_id": f"eq.{line_user_id}", "select": "id", "limit": 1}
                )

                if response.status_code == 200:
                    customers = response.json()
                    if customers:
                        return await self._get_contracts(client, customers[0]["id"])
                return []

        except Exception as e:
            print(f"⚠️ 查詢合約失敗: {e}")
            return []

    async def get_customer_payments(self, line_user_id: str) -> List[Dict[str, Any]]:
        """
        查詢客戶的繳費記錄

        Args:
            line_user_id: LINE 用戶 ID

        Returns:
            繳費記錄列表
        """
        if not self.enabled or not self.base_url:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 先查客戶 ID
                response = await client.get(
                    f"{self.base_url}/api/db/customers",
                    headers=self._get_headers(),
                    params={"line_user_id": f"eq.{line_user_id}", "select": "id", "limit": 1}
                )

                if response.status_code == 200:
                    customers = response.json()
                    if not customers:
                        return []

                    customer_id = customers[0]["id"]

                    # 查詢繳費記錄
                    pay_response = await client.get(
                        f"{self.base_url}/api/db/payments",
                        headers=self._get_headers(),
                        params={
                            "customer_id": f"eq.{customer_id}",
                            "order": "due_date.desc",
                            "limit": 50
                        }
                    )

                    if pay_response.status_code == 200:
                        payments = pay_response.json()
                        return [
                            {
                                "id": p.get("id"),
                                "pay_day": p.get("paid_at") or p.get("due_date"),
                                "pay_type": p.get("payment_type"),
                                "amount": float(p.get("amount", 0)),
                                "status": p.get("payment_status"),
                                "payment_method": p.get("payment_method"),
                            }
                            for p in payments
                        ]
                return []

        except Exception as e:
            print(f"⚠️ 查詢繳費記錄失敗: {e}")
            return []

    async def create_lead(
        self,
        line_user_id: str,
        display_name: str,
        inquiry_type: str = "general",
        notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        建立潛在客戶

        Args:
            line_user_id: LINE 用戶 ID
            display_name: LINE 顯示名稱
            inquiry_type: 詢問類型
            notes: 備註

        Returns:
            建立的客戶資料，失敗返回 None
        """
        if not self.enabled or not self.base_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 檢查是否已存在
                check_response = await client.get(
                    f"{self.base_url}/api/db/customers",
                    headers=self._get_headers(),
                    params={"line_user_id": f"eq.{line_user_id}", "limit": 1}
                )

                if check_response.status_code == 200:
                    existing = check_response.json()
                    if existing:
                        return {
                            "id": existing[0]["id"],
                            "name": existing[0].get("name"),
                            "is_new": False
                        }

                # 使用 MCP Server 建立客戶
                mcp_response = await client.post(
                    f"{self.base_url}/tools/call",
                    headers=self._get_headers(),
                    json={
                        "name": "crm_create_customer",
                        "parameters": {
                            "name": display_name or "LINE 用戶",
                            "branch_id": 1,  # 預設大忠館
                            "source_channel": f"line_brain_{inquiry_type}",
                            "line_user_id": line_user_id,
                        }
                    }
                )

                if mcp_response.status_code == 200:
                    result = mcp_response.json()
                    if result.get("success"):
                        return {
                            "id": result.get("data", {}).get("id"),
                            "name": display_name,
                            "is_new": True
                        }

                print(f"⚠️ 建立潛客失敗: {mcp_response.text}")
                return None

        except Exception as e:
            print(f"⚠️ 建立潛客失敗: {e}")
            return None

    async def notify_interaction(
        self,
        line_user_id: str,
        interaction_type: str,
        content: str
    ) -> bool:
        """
        通知 CRM 有新的互動記錄（目前僅記錄 log）

        Args:
            line_user_id: LINE 用戶 ID
            interaction_type: 互動類型
            content: 互動內容摘要

        Returns:
            是否成功
        """
        # 新 CRM 目前沒有互動記錄表，僅記錄 log
        print(f"📝 互動記錄: {line_user_id} - {interaction_type}: {content[:50]}...")
        return True

    async def forward_line_event(
        self,
        user_id: str,
        message_text: str,
        event_type: str = "message",
        postback_data: str = None
    ) -> Dict[str, Any]:
        """
        轉發 LINE 事件到 MCP Server 處理會議室預約

        Args:
            user_id: LINE 用戶 ID
            message_text: 訊息文字
            event_type: 事件類型 (message/postback)
            postback_data: postback 資料

        Returns:
            處理結果
        """
        if not self.enabled or not self.base_url:
            return {"success": False, "error": "CRM integration disabled"}

        try:
            # 注意：base_url 已經包含 /api，所以只需要 /line/forward
            url = f"{self.base_url}/line/forward"
            print(f"🔗 轉發到 MCP: {url}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json={
                        "user_id": user_id,
                        "message_text": message_text,
                        "event_type": event_type,
                        "postback_data": postback_data
                    }
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"⚠️ LINE 事件轉發失敗: {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}

        except httpx.TimeoutException:
            print(f"⚠️ LINE 事件轉發超時")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            print(f"⚠️ LINE 事件轉發失敗: {e}")
            return {"success": False, "error": str(e)}

    def format_customer_context(self, customer: Dict[str, Any]) -> str:
        """
        將客戶資料格式化為 AI Prompt 使用的上下文

        Args:
            customer: 客戶資料字典

        Returns:
            格式化的客戶資訊字串
        """
        if not customer:
            return ""

        parts = ["## 客戶資料（來自 CRM）\n"]

        # 基本資料
        name = customer.get("name", "未知")
        parts.append(f"**客戶名稱：** {name}")

        if customer.get("company_name"):
            parts.append(f"**公司名稱：** {customer['company_name']}")

        # 合約狀態
        contracts = customer.get("contracts", [])
        if contracts:
            parts.append(f"\n**現有合約：** {len(contracts)} 份")
            for contract in contracts[:3]:  # 最多顯示 3 份
                contract_status = contract.get("contract_status", "unknown")
                status_map = {
                    "active": "✅ 生效中",
                    "expired": "⏰ 已到期",
                    "pending": "⏳ 待生效",
                    "cancelled": "❌ 已取消"
                }
                status = status_map.get(contract_status, f"⚠️ {contract_status}")
                parts.append(f"  - {contract.get('project_name', '虛擬辦公室')}: {status}")
                if contract.get("next_pay_day"):
                    parts.append(f"    下次繳費日：{contract['next_pay_day']}")

        # 繳費狀態
        payment_status = customer.get("payment_status")
        if payment_status:
            if payment_status.get("overdue"):
                parts.append(f"\n⚠️ **逾期未繳：** {payment_status.get('overdue_amount', 0)} 元")
            elif payment_status.get("upcoming"):
                parts.append(f"\n📅 **即將到期：** {payment_status.get('upcoming_date')}")

        parts.append("\n---\n")
        return "\n".join(parts)


# 全域客戶端實例
_jungle_client: Optional[JungleClient] = None


def get_jungle_client() -> JungleClient:
    """取得 Jungle 客戶端單例"""
    global _jungle_client
    if _jungle_client is None:
        _jungle_client = JungleClient()
    return _jungle_client
