"""
Brain - LINE SDK 客戶端
封裝 LINE Messaging API
"""
from typing import Dict, Optional
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from config import settings


class LineClient:
    """LINE Messaging API 客戶端"""
    
    def __init__(self):
        """初始化 LINE 客戶端"""
        if not settings.LINE_CHANNEL_ACCESS_TOKEN or not settings.LINE_CHANNEL_SECRET:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET 未設定")
        
        # 設定 LINE SDK
        configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        self.api_client = ApiClient(configuration)
        self.messaging_api = MessagingApi(self.api_client)
        
        # Webhook Handler
        self.handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)
    
    async def send_text_message(self, user_id: str, text: str) -> bool:
        """
        發送文字訊息
        
        Args:
            user_id: LINE 用戶 ID
            text: 訊息內容
        
        Returns:
            是否發送成功
        """
        try:
            request = PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=text)]
            )
            self.messaging_api.push_message(request)
            return True
        except Exception as e:
            print(f"發送 LINE 訊息失敗: {str(e)}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """
        取得用戶資料
        
        Args:
            user_id: LINE 用戶 ID
        
        Returns:
            {
                "display_name": "用戶名稱",
                "user_id": "用戶 ID",
                "picture_url": "頭像 URL",
                "status_message": "狀態訊息"
            }
        """
        try:
            profile = self.messaging_api.get_profile(user_id)
            return {
                "display_name": profile.display_name,
                "user_id": profile.user_id,
                "picture_url": getattr(profile, 'picture_url', None),
                "status_message": getattr(profile, 'status_message', None),
            }
        except Exception as e:
            print(f"取得 LINE 用戶資料失敗: {str(e)}")
            return None
    
    def verify_signature(self, body: str, signature: str) -> bool:
        """
        驗證 Webhook 簽名
        
        Args:
            body: 請求 Body（字串格式）
            signature: X-Line-Signature Header
        
        Returns:
            簽名是否有效
        """
        try:
            self.handler.handle(body, signature)
            return True
        except Exception:
            return False


# 全域 LINE 客戶端實例
_line_client: Optional[LineClient] = None


def get_line_client() -> LineClient:
    """取得 LINE 客戶端單例"""
    global _line_client
    if _line_client is None:
        _line_client = LineClient()
    return _line_client
