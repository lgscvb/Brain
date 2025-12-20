"""
Brain - CRM API Client
統一封裝所有 CRM API 調用，避免參數名稱不一致的問題
"""
import os
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# CRM API 配置
CRM_API_URL = os.getenv("CRM_API_URL", "https://auto.yourspce.org")
CRM_TIMEOUT = 30.0

# CRM API 期望的參數名稱（不是 MCP 的 "arguments"）
CRM_TOOL_PARAM_KEY = "parameters"


class CRMClient:
    """CRM API 客戶端"""

    def __init__(self, base_url: str = None, timeout: float = None):
        self.base_url = base_url or CRM_API_URL
        self.timeout = timeout or CRM_TIMEOUT

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        調用 CRM MCP 工具

        Args:
            tool_name: 工具名稱 (如 quote_create_from_service_plans)
            **kwargs: 工具參數

        Returns:
            工具執行結果

        Example:
            result = await crm.call_tool(
                "quote_create_from_service_plans",
                branch_id=1,
                service_codes=["virtual_office_2year"]
            )
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tools/call",
                    json={
                        "tool": tool_name,
                        CRM_TOOL_PARAM_KEY: kwargs  # 使用統一的參數名稱
                    }
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"CRM tool '{tool_name}' HTTP error: {e.response.status_code}")
            raise CRMError(f"CRM API 錯誤: {e.response.status_code}")
        except Exception as e:
            logger.error(f"CRM tool '{tool_name}' error: {e}")
            raise CRMError(f"CRM 調用失敗: {e}")

    async def get_db(self, table: str, params: Dict[str, str] = None) -> List[Dict]:
        """
        查詢 CRM 資料庫（透過 PostgREST）

        Args:
            table: 資料表或視圖名稱
            params: PostgREST 查詢參數

        Returns:
            查詢結果列表
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/db/{table}",
                    params=params
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"CRM DB query '{table}' error: {e}")
            raise CRMError(f"資料庫查詢失敗: {e}")

    # ========== 常用工具快捷方法 ==========

    async def list_service_plans(
        self,
        category: str = None,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """取得服務價格列表"""
        params = {"is_active": is_active}
        if category:
            params["category"] = category
        return await self.call_tool("service_plan_list", **params)

    async def create_quote_from_service_plans(
        self,
        branch_id: int,
        service_codes: List[str],
        customer_name: str = None,
        customer_phone: str = None,
        line_user_id: str = None,
        discount_amount: float = 0,
        discount_note: str = None,
        internal_notes: str = None
    ) -> Dict[str, Any]:
        """根據服務代碼建立報價單"""
        return await self.call_tool(
            "quote_create_from_service_plans",
            branch_id=branch_id,
            service_codes=service_codes,
            customer_name=customer_name,
            customer_phone=customer_phone,
            line_user_id=line_user_id,
            discount_amount=discount_amount,
            discount_note=discount_note,
            internal_notes=internal_notes
        )

    async def send_line_message(
        self,
        line_user_id: str,
        message: str,
        message_type: str = "text"
    ) -> Dict[str, Any]:
        """發送 LINE 訊息"""
        return await self.call_tool(
            "line_send_message",
            line_user_id=line_user_id,
            message=message,
            message_type=message_type
        )


class CRMError(Exception):
    """CRM API 錯誤"""
    pass


# 全域單例
_crm_client: Optional[CRMClient] = None


def get_crm_client() -> CRMClient:
    """取得 CRM 客戶端單例"""
    global _crm_client
    if _crm_client is None:
        _crm_client = CRMClient()
    return _crm_client
