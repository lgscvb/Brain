"""
Brain - 照片 API 路由
提供照片管理和發送功能

端點：
- GET  /api/photos              列出所有照片
- GET  /api/photos/{category}   列出某分類照片
- POST /api/photos/send         手動發送照片給客戶
- POST /api/photos/upload       上傳新照片
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from services.r2_client import get_r2_photo_client
from services.photo_service import (
    get_photos_by_category,
    send_photos_to_user,
    send_category_menu,
    CATEGORY_NAMES
)


router = APIRouter()


# === Request/Response Models ===

class SendPhotoRequest(BaseModel):
    """發送照片請求"""
    user_id: str
    category: str = "all"  # exterior, private_office, coworking, facilities, all
    max_photos: int = 10


class UploadPhotoRequest(BaseModel):
    """上傳照片請求（Base64）"""
    file_name: str
    category: str
    content_base64: str
    content_type: str = "image/jpeg"


# === API Endpoints ===

@router.get("/photos")
async def list_photos(category: Optional[str] = None):
    """
    列出照片

    Query params:
        category: 分類篩選（可選）
    """
    cat = category if category else "all"
    result = await get_photos_by_category(cat)

    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "取得照片失敗"),
            "photos": [],
            "categories": list(CATEGORY_NAMES.keys())
        }

    return {
        "success": True,
        "category": cat,
        "photos": result.get("photos", []),
        "count": result.get("count", 0),
        "categories": list(CATEGORY_NAMES.keys()),
        "category_names": CATEGORY_NAMES
    }


@router.get("/photos/{category}")
async def list_photos_by_category(category: str):
    """
    列出某分類的照片

    Path params:
        category: 分類（exterior, private_office, coworking, facilities）
    """
    if category not in CATEGORY_NAMES and category != "all":
        raise HTTPException(
            status_code=400,
            detail=f"無效的分類，可用: {', '.join(CATEGORY_NAMES.keys())}"
        )

    result = await get_photos_by_category(category)

    return {
        "success": result.get("success", False),
        "category": category,
        "category_name": CATEGORY_NAMES.get(category, category),
        "photos": result.get("photos", []),
        "count": result.get("count", 0),
        "error": result.get("error") if not result.get("success") else None
    }


@router.post("/photos/send")
async def send_photos(request: SendPhotoRequest):
    """
    手動發送照片給客戶

    Body:
        user_id: LINE 用戶 ID
        category: 分類（預設 all）
        max_photos: 最多幾張（預設 10）
    """
    if not request.user_id:
        raise HTTPException(status_code=400, detail="user_id 為必填")

    result = await send_photos_to_user(
        user_id=request.user_id,
        category=request.category,
        max_photos=request.max_photos
    )

    return result


@router.post("/photos/send-menu")
async def send_photo_menu(user_id: str):
    """
    發送分類選單給客戶

    Query params:
        user_id: LINE 用戶 ID
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id 為必填")

    result = await send_category_menu(user_id)
    return result


@router.post("/photos/upload")
async def upload_photo(request: UploadPhotoRequest):
    """
    上傳新照片到 R2

    Body:
        file_name: 檔案名稱
        category: 分類
        content_base64: Base64 編碼的圖片內容
        content_type: MIME 類型
    """
    import base64

    if request.category not in CATEGORY_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"無效的分類，可用: {', '.join(CATEGORY_NAMES.keys())}"
        )

    try:
        file_bytes = base64.b64decode(request.content_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Base64 解碼失敗: {e}")

    r2_client = get_r2_photo_client()

    if not r2_client.is_configured():
        raise HTTPException(status_code=500, detail="R2 未配置")

    result = r2_client.upload_photo_bytes(
        file_bytes=file_bytes,
        file_name=request.file_name,
        category=request.category,
        content_type=request.content_type
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "上傳失敗"))

    return {
        "success": True,
        "message": f"照片上傳成功: {request.file_name}",
        "r2_path": result.get("r2_path"),
        "category": request.category
    }


@router.get("/photos/categories")
async def get_categories():
    """
    取得所有照片分類
    """
    return {
        "success": True,
        "categories": [
            {"key": k, "name": v}
            for k, v in CATEGORY_NAMES.items()
            if k != "all"
        ],
        "all_option": {"key": "all", "name": "全部照片"}
    }


@router.get("/photos/status")
async def get_photo_status():
    """
    取得照片服務狀態（R2 配置狀態、照片數量等）
    """
    r2_client = get_r2_photo_client()
    is_configured = r2_client.is_configured()

    status = {
        "success": True,
        "r2_configured": is_configured,
        "bucket": r2_client.bucket if is_configured else None,
        "prefix": r2_client.prefix if is_configured else None,
    }

    if is_configured:
        # 取得各分類照片數量
        category_counts = {}
        for cat in CATEGORY_NAMES.keys():
            if cat == "all":
                continue
            result = await get_photos_by_category(cat)
            category_counts[cat] = result.get("count", 0)

        status["category_counts"] = category_counts
        status["total_photos"] = sum(category_counts.values())

    return status
