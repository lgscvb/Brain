"""
Brain - 媒體處理服務
處理 LINE 傳送的圖片、PDF 等媒體檔案

流程：
1. 從 LINE 下載媒體內容
2. 上傳到 R2 存儲桶
3. OCR 提取文字（圖片用 Claude Vision，PDF 用 PyMuPDF）
4. 更新 Attachment 記錄

這個服務的職責：
- 協調 LINE Client（下載）、R2 Client（存儲）、Claude Client（OCR）
- 提供統一的媒體處理介面給 Webhook 使用
"""

import base64
import logging
from datetime import datetime
from typing import Dict, Optional

from config import settings

logger = logging.getLogger(__name__)

# OCR 提示詞模板
OCR_PROMPT_IMAGE = """請仔細檢視這張圖片，提取所有可見的文字內容。

規則：
1. 如果是名片，請提取：姓名、公司、職稱、電話、Email、地址等聯絡資訊，用結構化格式呈現
2. 如果是文件/表單，請保持原有的格式和層次結構
3. 如果是截圖/對話記錄，請完整提取對話內容
4. 如果圖片中沒有文字，請描述圖片的主要內容（50字以內）
5. 如果文字模糊難以辨識，請標註 [難以辨識]

請直接輸出提取的內容，不要加任何前綴說明。"""

OCR_PROMPT_SCANNED_PDF = """這是一份掃描的 PDF 文件頁面。請提取所有可見的文字內容。

規則：
1. 保持文件的原有格式和層次結構
2. 如果有表格，請用表格格式呈現
3. 如果文字模糊難以辨識，請標註 [難以辨識]
4. 忽略頁碼、浮水印等非主要內容

請直接輸出提取的內容，不要加任何前綴說明。"""


class MediaService:
    """媒體處理服務"""

    def __init__(self):
        # 延遲導入，避免循環依賴
        from services.line_client import get_line_client
        from services.r2_client import get_r2_photo_client
        from services.claude_client import get_claude_client

        self.line_client = get_line_client()
        self.r2_client = get_r2_photo_client()
        self.claude_client = get_claude_client()

    async def process_image(
        self,
        line_message_id: str,
        sender_id: str,
        mime_type: str = "image/jpeg"
    ) -> Dict:
        """
        處理圖片：下載 → R2 → OCR

        Args:
            line_message_id: LINE 訊息 ID（用於下載媒體）
            sender_id: 發送者 ID（用於檔名）
            mime_type: 圖片 MIME 類型

        Returns:
            {
                "success": True/False,
                "r2_path": str,
                "r2_url": str,
                "ocr_text": str,
                "file_size": int,
                "error": str (失敗時)
            }
        """
        logger.info(f"[MediaService] 開始處理圖片 message_id={line_message_id}")

        # Step 1: 從 LINE 下載媒體
        download_result = self.line_client.download_media(line_message_id)
        if not download_result.get("success"):
            error_msg = download_result.get("error", "下載失敗")
            logger.error(f"[MediaService] 下載圖片失敗: {error_msg}")
            return {
                "success": False,
                "error": f"下載失敗: {error_msg}",
                "download_status": "failed"
            }

        image_bytes = download_result["content"]
        file_size = len(image_bytes)
        logger.info(f"[MediaService] 圖片下載完成，大小: {file_size} bytes")

        # Step 2: 上傳到 R2
        # 產生唯一檔名：{sender_id前10字}_{timestamp}.{ext}
        ext = mime_type.split("/")[-1] if "/" in mime_type else "jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{sender_id[:10]}_{timestamp}.{ext}"

        upload_result = self.r2_client.upload_photo_bytes(
            file_bytes=image_bytes,
            file_name=file_name,
            category="line-uploads",  # 專用分類
            content_type=mime_type
        )

        if not upload_result.get("success"):
            error_msg = upload_result.get("error", "上傳失敗")
            logger.error(f"[MediaService] R2 上傳失敗: {error_msg}")
            return {
                "success": False,
                "error": f"R2 上傳失敗: {error_msg}",
                "download_status": "completed"
            }

        r2_path = upload_result["r2_path"]
        logger.info(f"[MediaService] R2 上傳完成: {r2_path}")

        # 產生簽名 URL（2 週有效）
        url_result = self.r2_client.get_signed_url(r2_path)
        r2_url = url_result.get("signed_url", "")
        r2_url_expires_at = url_result.get("expires_at")

        # Step 3: OCR（使用 Claude Vision）
        ocr_text = ""
        ocr_status = "pending"

        try:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            ocr_result = await self.claude_client.analyze_image(
                image_base64=image_base64,
                prompt=OCR_PROMPT_IMAGE,
                media_type=mime_type
            )

            if ocr_result.get("success"):
                ocr_text = ocr_result.get("content", "")
                ocr_status = "completed"
                logger.info(f"[MediaService] OCR 完成，提取 {len(ocr_text)} 字")
            else:
                ocr_status = "failed"
                logger.warning(f"[MediaService] OCR 失敗: {ocr_result.get('error')}")

        except Exception as e:
            ocr_status = "failed"
            logger.error(f"[MediaService] OCR 異常: {e}")

        return {
            "success": True,
            "r2_path": r2_path,
            "r2_url": r2_url,
            "r2_url_expires_at": r2_url_expires_at,
            "ocr_text": ocr_text,
            "ocr_status": ocr_status,
            "file_size": file_size,
            "file_name": file_name,
            "download_status": "completed"
        }

    async def process_pdf(
        self,
        line_message_id: str,
        sender_id: str,
        file_name: str = None
    ) -> Dict:
        """
        處理 PDF：下載 → R2 → 文字提取

        優先使用 PyMuPDF 提取文字（快速、準確）
        如果是掃描檔（無文字層），則轉為圖片使用 Vision OCR

        Args:
            line_message_id: LINE 訊息 ID
            sender_id: 發送者 ID
            file_name: 原始檔名（可選）

        Returns:
            處理結果
        """
        logger.info(f"[MediaService] 開始處理 PDF message_id={line_message_id}")

        # Step 1: 從 LINE 下載
        download_result = self.line_client.download_media(line_message_id)
        if not download_result.get("success"):
            error_msg = download_result.get("error", "下載失敗")
            logger.error(f"[MediaService] 下載 PDF 失敗: {error_msg}")
            return {
                "success": False,
                "error": f"下載失敗: {error_msg}",
                "download_status": "failed"
            }

        pdf_bytes = download_result["content"]
        file_size = len(pdf_bytes)

        # 檢查檔案大小限制（10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            logger.warning(f"[MediaService] PDF 檔案過大: {file_size} bytes (max: {max_size})")
            return {
                "success": False,
                "error": f"PDF 檔案過大（{file_size // 1024 // 1024}MB），上限為 10MB",
                "download_status": "completed"
            }

        logger.info(f"[MediaService] PDF 下載完成，大小: {file_size} bytes")

        # Step 2: 上傳到 R2
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not file_name:
            file_name = f"{sender_id[:10]}_{timestamp}.pdf"
        else:
            # 加上 timestamp 避免重複
            base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
            file_name = f"{base_name}_{timestamp}.pdf"

        upload_result = self.r2_client.upload_photo_bytes(
            file_bytes=pdf_bytes,
            file_name=file_name,
            category="line-uploads",
            content_type="application/pdf"
        )

        if not upload_result.get("success"):
            error_msg = upload_result.get("error", "上傳失敗")
            logger.error(f"[MediaService] R2 上傳 PDF 失敗: {error_msg}")
            return {
                "success": False,
                "error": f"R2 上傳失敗: {error_msg}",
                "download_status": "completed"
            }

        r2_path = upload_result["r2_path"]
        logger.info(f"[MediaService] PDF R2 上傳完成: {r2_path}")

        # 產生簽名 URL
        url_result = self.r2_client.get_signed_url(r2_path)
        r2_url = url_result.get("signed_url", "")
        r2_url_expires_at = url_result.get("expires_at")

        # Step 3: 提取文字
        ocr_text = ""
        ocr_status = "pending"

        try:
            ocr_text = await self._extract_pdf_text(pdf_bytes)
            if ocr_text:
                ocr_status = "completed"
                logger.info(f"[MediaService] PDF 文字提取完成，共 {len(ocr_text)} 字")
            else:
                ocr_status = "failed"
                logger.warning("[MediaService] PDF 無法提取文字（可能是純掃描檔）")

        except Exception as e:
            ocr_status = "failed"
            logger.error(f"[MediaService] PDF 文字提取異常: {e}")

        return {
            "success": True,
            "r2_path": r2_path,
            "r2_url": r2_url,
            "r2_url_expires_at": r2_url_expires_at,
            "ocr_text": ocr_text,
            "ocr_status": ocr_status,
            "file_size": file_size,
            "file_name": file_name,
            "download_status": "completed"
        }

    async def _extract_pdf_text(self, pdf_bytes: bytes, max_pages: int = 10) -> str:
        """
        從 PDF 提取文字

        優先使用 PyMuPDF（快速），如果無文字則嘗試 Vision OCR（慢但強）

        Args:
            pdf_bytes: PDF 二進位內容
            max_pages: 最多處理幾頁（避免過大的 PDF）

        Returns:
            提取的文字內容
        """
        extracted_text = ""

        # 嘗試使用 PyMuPDF 提取文字
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = min(len(doc), max_pages)

            text_parts = []
            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"--- 第 {page_num + 1} 頁 ---\n{page_text}")

            doc.close()

            if text_parts:
                extracted_text = "\n\n".join(text_parts)
                logger.info(f"[MediaService] PyMuPDF 提取成功，{page_count} 頁")
                return extracted_text

            # 如果 PyMuPDF 沒提取到文字，可能是掃描檔
            # 嘗試把第一頁轉成圖片用 Vision OCR
            logger.info("[MediaService] PDF 無文字層，嘗試 Vision OCR")

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if len(doc) > 0:
                page = doc[0]
                # 轉成圖片（72 dpi 足夠 OCR）
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                doc.close()

                # 使用 Vision OCR
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                ocr_result = await self.claude_client.analyze_image(
                    image_base64=img_base64,
                    prompt=OCR_PROMPT_SCANNED_PDF,
                    media_type="image/png"
                )

                if ocr_result.get("success"):
                    extracted_text = ocr_result.get("content", "")
                    logger.info(f"[MediaService] Vision OCR 成功，提取 {len(extracted_text)} 字")

        except ImportError:
            logger.warning("[MediaService] PyMuPDF 未安裝，無法處理 PDF")
        except Exception as e:
            logger.error(f"[MediaService] PDF 處理失敗: {e}")

        return extracted_text

    async def process_file(
        self,
        line_message_id: str,
        sender_id: str,
        file_name: str,
        file_size: int
    ) -> Dict:
        """
        處理一般檔案（非圖片、非 PDF）

        目前只做下載和存儲，不做內容分析

        Args:
            line_message_id: LINE 訊息 ID
            sender_id: 發送者 ID
            file_name: 原始檔名
            file_size: 檔案大小

        Returns:
            處理結果
        """
        logger.info(f"[MediaService] 處理檔案 {file_name} ({file_size} bytes)")

        # 檢查檔案大小限制（10MB）
        max_size = 10 * 1024 * 1024
        if file_size > max_size:
            return {
                "success": False,
                "error": f"檔案過大（{file_size // 1024 // 1024}MB），上限為 10MB",
                "download_status": "skipped"
            }

        # 下載
        download_result = self.line_client.download_media(line_message_id)
        if not download_result.get("success"):
            return {
                "success": False,
                "error": download_result.get("error", "下載失敗"),
                "download_status": "failed"
            }

        file_bytes = download_result["content"]

        # 判斷 content type
        ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
        content_type_map = {
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
            'csv': 'text/csv',
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')

        # 上傳到 R2
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
        unique_file_name = f"{base_name}_{timestamp}.{ext}" if ext else f"{base_name}_{timestamp}"

        upload_result = self.r2_client.upload_photo_bytes(
            file_bytes=file_bytes,
            file_name=unique_file_name,
            category="line-uploads",
            content_type=content_type
        )

        if not upload_result.get("success"):
            return {
                "success": False,
                "error": upload_result.get("error", "上傳失敗"),
                "download_status": "completed"
            }

        r2_path = upload_result["r2_path"]

        # 產生簽名 URL
        url_result = self.r2_client.get_signed_url(r2_path)

        return {
            "success": True,
            "r2_path": r2_path,
            "r2_url": url_result.get("signed_url", ""),
            "r2_url_expires_at": url_result.get("expires_at"),
            "ocr_text": "",  # 一般檔案不做 OCR
            "ocr_status": "skipped",
            "file_size": len(file_bytes),
            "file_name": unique_file_name,
            "download_status": "completed"
        }


# 全域服務實例
_media_service: Optional[MediaService] = None


def get_media_service() -> MediaService:
    """取得媒體處理服務單例"""
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service
