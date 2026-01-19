"""
Brain - Cloudflare R2 Client
照片存儲服務，與 v2-hj-crm 共用同一個 R2 Bucket

功能：
- upload_photo: 上傳照片到 R2
- get_signed_url: 產生簽名下載 URL（2 週過期）
- list_photos: 列出照片
- delete_photo: 刪除照片
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import base64

from config import settings

logger = logging.getLogger(__name__)

# R2 Endpoint
R2_ENDPOINT = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if settings.R2_ACCOUNT_ID else ""


def get_r2_client():
    """取得 R2 客戶端（boto3 S3 client）"""
    if not settings.R2_ACCOUNT_ID or not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        logger.warning("R2 credentials not configured")
        return None

    try:
        import boto3
        from botocore.config import Config

        client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto'  # R2 使用 'auto'
        )
        return client
    except ImportError:
        logger.error("boto3 not installed. Run: pip install boto3")
        return None
    except Exception as e:
        logger.error(f"Failed to create R2 client: {e}")
        return None


class R2PhotoClient:
    """R2 照片存儲客戶端"""

    def __init__(self):
        self.client = get_r2_client()
        self.bucket = settings.R2_BUCKET_NAME
        self.prefix = settings.R2_PHOTO_PREFIX
        self.url_expiry = settings.R2_URL_EXPIRY

    def is_configured(self) -> bool:
        """檢查 R2 是否已配置"""
        return self.client is not None

    def upload_photo(
        self,
        file_path: str,
        category: str,
        title: str = None,
        content_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        上傳照片到 R2

        Args:
            file_path: 本地照片路徑
            category: 分類（exterior, private_office, coworking, facilities）
            title: 照片標題（用於顯示）
            content_type: MIME 類型

        Returns:
            上傳結果，包含 r2_path
        """
        if not self.client:
            return {
                "success": False,
                "error": "R2 未配置",
                "code": "NOT_CONFIGURED"
            }

        try:
            # 讀取照片
            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            file_name = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # R2 路徑：brain-photos/{category}/{timestamp}_{filename}
            r2_path = f"{self.prefix}/{category}/{timestamp}_{file_name}"

            # 上傳到 R2
            self.client.put_object(
                Bucket=self.bucket,
                Key=r2_path,
                Body=file_bytes,
                ContentType=content_type
            )

            logger.info(f"照片上傳成功: {r2_path}")

            return {
                "success": True,
                "r2_path": r2_path,
                "file_name": file_name,
                "category": category,
                "file_size": len(file_bytes)
            }

        except FileNotFoundError:
            return {
                "success": False,
                "error": f"找不到檔案: {file_path}",
                "code": "FILE_NOT_FOUND"
            }
        except Exception as e:
            logger.error(f"上傳照片失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "UPLOAD_FAILED"
            }

    def upload_photo_bytes(
        self,
        file_bytes: bytes,
        file_name: str,
        category: str,
        content_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        上傳照片（bytes 格式）

        Args:
            file_bytes: 照片 bytes
            file_name: 檔案名稱
            category: 分類
            content_type: MIME 類型

        Returns:
            上傳結果
        """
        if not self.client:
            return {
                "success": False,
                "error": "R2 未配置",
                "code": "NOT_CONFIGURED"
            }

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            r2_path = f"{self.prefix}/{category}/{timestamp}_{file_name}"

            self.client.put_object(
                Bucket=self.bucket,
                Key=r2_path,
                Body=file_bytes,
                ContentType=content_type
            )

            logger.info(f"照片上傳成功: {r2_path}")

            return {
                "success": True,
                "r2_path": r2_path,
                "file_name": file_name,
                "category": category,
                "file_size": len(file_bytes)
            }

        except Exception as e:
            logger.error(f"上傳照片失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "UPLOAD_FAILED"
            }

    def get_signed_url(self, r2_path: str, expiry_seconds: int = None) -> Dict[str, Any]:
        """
        產生簽名下載 URL

        Args:
            r2_path: R2 上的照片路徑
            expiry_seconds: 過期時間（秒），預設使用設定值

        Returns:
            包含 signed_url 的結果
        """
        if not self.client:
            return {
                "success": False,
                "error": "R2 未配置",
                "code": "NOT_CONFIGURED"
            }

        if expiry_seconds is None:
            expiry_seconds = self.url_expiry

        try:
            signed_url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': r2_path
                },
                ExpiresIn=expiry_seconds
            )

            expires_at = datetime.now().timestamp() + expiry_seconds

            return {
                "success": True,
                "signed_url": signed_url,
                "r2_path": r2_path,
                "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
                "expiry_seconds": expiry_seconds
            }

        except Exception as e:
            logger.error(f"產生簽名 URL 失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "URL_GENERATION_FAILED"
            }

    def list_photos(self, category: str = None) -> Dict[str, Any]:
        """
        列出照片

        Args:
            category: 分類篩選（可選）

        Returns:
            照片列表
        """
        if not self.client:
            return {
                "success": False,
                "error": "R2 未配置",
                "code": "NOT_CONFIGURED"
            }

        try:
            prefix = self.prefix
            if category:
                prefix = f"{self.prefix}/{category}/"

            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )

            photos = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                # 解析分類
                parts = key.replace(f"{self.prefix}/", "").split("/")
                photo_category = parts[0] if len(parts) > 1 else "uncategorized"
                file_name = parts[-1] if parts else key

                photos.append({
                    "r2_path": key,
                    "file_name": file_name,
                    "category": photo_category,
                    "file_size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat() if obj.get('LastModified') else None
                })

            return {
                "success": True,
                "photos": photos,
                "count": len(photos)
            }

        except Exception as e:
            logger.error(f"列出照片失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "LIST_FAILED"
            }

    def delete_photo(self, r2_path: str) -> Dict[str, Any]:
        """
        刪除照片

        Args:
            r2_path: R2 上的照片路徑

        Returns:
            刪除結果
        """
        if not self.client:
            return {
                "success": False,
                "error": "R2 未配置",
                "code": "NOT_CONFIGURED"
            }

        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=r2_path
            )

            logger.info(f"照片已刪除: {r2_path}")

            return {
                "success": True,
                "r2_path": r2_path,
                "message": "照片已刪除"
            }

        except Exception as e:
            logger.error(f"刪除照片失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "code": "DELETE_FAILED"
            }


# 全域客戶端實例
_r2_photo_client: Optional[R2PhotoClient] = None


def get_r2_photo_client() -> R2PhotoClient:
    """取得 R2 照片客戶端單例"""
    global _r2_photo_client
    if _r2_photo_client is None:
        _r2_photo_client = R2PhotoClient()
    return _r2_photo_client
