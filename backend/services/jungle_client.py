"""
Brain - Jungle CRM API 客戶端
用於查詢 Jungle 系統的客戶資料、合約、繳費記錄
"""
import httpx
from typing import Optional, Dict, Any, List
from config import settings


class JungleClient:
    """Jungle CRM API 客戶端"""

    def __init__(self):
        """初始化客戶端"""
        self.base_url = settings.JUNGLE_API_URL
        self.api_key = settings.JUNGLE_API_KEY
        self.enabled = settings.ENABLE_JUNGLE_INTEGRATION
        self.timeout = 10.0  # 秒

    def _get_headers(self) -> Dict[str, str]:
        """取得請求標頭"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_customer_by_line_id(self, line_user_id: str) -> Optional[Dict[str, Any]]:
        """
        透過 LINE userId 查詢客戶資料

        Args:
            line_user_id: LINE 用戶 ID

        Returns:
            客戶資料字典，包含：
            - id: 客戶 ID
            - name: 客戶名稱
            - phone: 電話
            - email: 信箱
            - company_name: 公司名稱
            - contracts: 合約列表
            - payment_status: 繳費狀態
            如果找不到則返回 None
        """
        if not self.enabled or not self.base_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/brain/customer/{line_user_id}",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("data")
                elif response.status_code == 404:
                    # 客戶不存在
                    return None
                else:
                    print(f"⚠️ Jungle API 錯誤: {response.status_code} - {response.text}")
                    return None

        except httpx.TimeoutException:
            print(f"⚠️ Jungle API 超時")
            return None
        except Exception as e:
            print(f"⚠️ Jungle API 連線失敗: {e}")
            return None

    async def get_customer_contracts(self, line_user_id: str) -> List[Dict[str, Any]]:
        """
        查詢客戶的所有合約

        Args:
            line_user_id: LINE 用戶 ID

        Returns:
            合約列表，每個合約包含：
            - id: 合約 ID
            - project_name: 專案名稱
            - contract_type: 合約類型
            - start_day: 開始日期
            - end_day: 結束日期
            - status: 合約狀態
            - next_pay_day: 下次繳費日
        """
        if not self.enabled or not self.base_url:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/brain/customer/{line_user_id}/contracts",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
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
                response = await client.get(
                    f"{self.base_url}/brain/customer/{line_user_id}/payments",
                    headers=self._get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
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
        建立潛在客戶（從 Brain 轉交給 Jungle）

        Args:
            line_user_id: LINE 用戶 ID
            display_name: LINE 顯示名稱
            inquiry_type: 詢問類型 (general, registration, coworking, meeting_room)
            notes: 備註（對話摘要）

        Returns:
            建立的客戶資料，失敗返回 None
        """
        if not self.enabled or not self.base_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/brain/leads",
                    headers=self._get_headers(),
                    json={
                        "line_user_id": line_user_id,
                        "display_name": display_name,
                        "inquiry_type": inquiry_type,
                        "notes": notes
                    }
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    return data.get("data")
                else:
                    print(f"⚠️ 建立潛客失敗: {response.status_code} - {response.text}")
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
        通知 Jungle 有新的互動記錄

        Args:
            line_user_id: LINE 用戶 ID
            interaction_type: 互動類型 (message, reply, call)
            content: 互動內容摘要

        Returns:
            是否成功
        """
        if not self.enabled or not self.base_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/brain/interactions",
                    headers=self._get_headers(),
                    json={
                        "line_user_id": line_user_id,
                        "interaction_type": interaction_type,
                        "content": content
                    }
                )

                return response.status_code in [200, 201]

        except Exception as e:
            print(f"⚠️ 通知互動失敗: {e}")
            return False

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
                status = "✅ 有效" if contract.get("status") == "active" else "⚠️ " + contract.get("status", "未知")
                parts.append(f"  - {contract.get('project_name', '未命名')}: {status}")
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
