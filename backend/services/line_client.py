"""
Brain - LINE SDK 客戶端
封裝 LINE Messaging API
"""
import logging
from typing import Dict, Optional
from linebot.v3 import WebhookHandler

logger = logging.getLogger(__name__)
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from config import settings


class LineClientError(Exception):
    """LINE API 錯誤"""
    pass


class LineClient:
    """LINE Messaging API 客戶端"""
    
    def __init__(self):
        """初始化 LINE 客戶端"""
        self.mock_mode = False

        if not settings.LINE_CHANNEL_ACCESS_TOKEN or not settings.LINE_CHANNEL_SECRET:
            logger.warning("LINE_CHANNEL_ACCESS_TOKEN 或 LINE_CHANNEL_SECRET 未設定，使用模擬模式")
            self.mock_mode = True
            self.api_client = None
            self.messaging_api = None
            self.handler = None
        else:
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
        if self.mock_mode:
            logger.debug(f"[模擬模式] 發送 LINE 訊息給 {user_id}: {text[:50]}...")
            return True

        try:
            request = PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=text)]
            )
            self.messaging_api.push_message(request)
            return True
        except Exception as e:
            logger.error(f"發送 LINE 訊息失敗: {e}")
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
        if self.mock_mode:
            return {
                "display_name": "測試用戶",
                "user_id": user_id,
                "picture_url": None,
                "status_message": None,
            }
        
        try:
            profile = self.messaging_api.get_profile(user_id)
            return {
                "display_name": profile.display_name,
                "user_id": profile.user_id,
                "picture_url": getattr(profile, 'picture_url', None),
                "status_message": getattr(profile, 'status_message', None),
            }
        except Exception as e:
            logger.warning(f"取得 LINE 用戶資料失敗: {e}")
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
        if self.mock_mode:
            return True

        import hashlib
        import hmac
        import base64

        try:
            # 使用 HMAC-SHA256 驗證簽名
            channel_secret = settings.LINE_CHANNEL_SECRET.encode('utf-8')
            body_bytes = body.encode('utf-8')

            hash_value = hmac.new(channel_secret, body_bytes, hashlib.sha256).digest()
            expected_signature = base64.b64encode(hash_value).decode('utf-8')

            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"簽名驗證失敗: {e}")
            return False

    async def send_flex_message(self, user_id: str, alt_text: str, contents: Dict) -> bool:
        """
        發送 Flex Message（互動式訊息）

        Args:
            user_id: LINE 用戶 ID
            alt_text: 替代文字（用於通知和不支援 Flex 的裝置）
            contents: Flex Message 內容（JSON 格式）

        Returns:
            是否發送成功
        """
        if self.mock_mode:
            logger.debug(f"[模擬模式] 發送 Flex Message 給 {user_id}: {alt_text}")
            return True

        try:
            # 將 dict 轉換為 FlexContainer
            flex_container = FlexContainer.from_dict(contents)
            flex_message = FlexMessage(alt_text=alt_text, contents=flex_container)

            request = PushMessageRequest(
                to=user_id,
                messages=[flex_message]
            )
            self.messaging_api.push_message(request)
            return True
        except Exception as e:
            logger.error(f"發送 Flex Message 失敗: {e}")
            return False

    async def reply_message(self, user_id: str, text: str) -> bool:
        """
        回覆訊息（使用 Push API）

        Args:
            user_id: LINE 用戶 ID
            text: 訊息內容

        Returns:
            是否發送成功
        """
        return await self.send_text_message(user_id, text)


# 全域 LINE 客戶端實例
_line_client: Optional[LineClient] = None


def get_line_client() -> LineClient:
    """取得 LINE 客戶端單例"""
    global _line_client
    if _line_client is None:
        _line_client = LineClient()
    return _line_client
