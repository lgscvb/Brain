"""
Brain - 照片服務
處理照片的取得、發送等邏輯

功能：
- get_photos_by_category: 取得某分類的照片（含簽名 URL）
- send_photos_to_user: 發送照片 Flex Message 給用戶
"""

import logging
from typing import Dict, Any, List, Optional

from services.r2_client import get_r2_photo_client
from services.line_client import get_line_client
from services.flex_templates import (
    build_photo_carousel,
    build_category_menu,
    build_photo_intro_message,
    CATEGORY_NAMES
)

logger = logging.getLogger(__name__)


# 預設照片（如果 R2 沒有照片，使用這些）
# 這些是直接上傳到 R2 後的路徑，需要執行 upload_photos.py 後更新
DEFAULT_PHOTOS = {
    "exterior": [
        {"r2_path": "brain-photos/exterior/building.jpg", "title": "明錩大亨大樓外觀"},
    ],
    "private_office": [
        {"r2_path": "brain-photos/private_office/d_office.jpg", "title": "獨立辦公室 D辦"},
        {"r2_path": "brain-photos/private_office/e_office.jpg", "title": "獨立辦公室 E辦"},
    ],
    "coworking": [
        {"r2_path": "brain-photos/coworking/reception.jpg", "title": "共享空間櫃檯"},
        {"r2_path": "brain-photos/coworking/workspace.jpg", "title": "共享空間"},
    ],
    "facilities": [
        {"r2_path": "brain-photos/facilities/restroom.jpg", "title": "廁所"},
        {"r2_path": "brain-photos/facilities/printer.jpg", "title": "事務機"},
    ],
}


async def get_photos_by_category(category: str = "all") -> Dict[str, Any]:
    """
    取得某分類的照片（含簽名 URL）

    Args:
        category: 分類（exterior, private_office, coworking, facilities, all）

    Returns:
        包含照片列表的結果
    """
    r2_client = get_r2_photo_client()

    if not r2_client.is_configured():
        logger.warning("R2 未配置，使用空照片列表")
        return {
            "success": False,
            "error": "R2 未配置",
            "photos": []
        }

    try:
        # 從 R2 取得照片列表
        if category == "all":
            list_result = r2_client.list_photos()
        else:
            list_result = r2_client.list_photos(category=category)

        if not list_result.get("success"):
            return {
                "success": False,
                "error": list_result.get("error", "取得照片列表失敗"),
                "photos": []
            }

        photos_raw = list_result.get("photos", [])

        # 為每張照片產生簽名 URL
        photos = []
        for photo in photos_raw:
            url_result = r2_client.get_signed_url(photo["r2_path"])
            if url_result.get("success"):
                photos.append({
                    "r2_path": photo["r2_path"],
                    "file_name": photo["file_name"],
                    "category": photo["category"],
                    "title": get_photo_title(photo["file_name"], photo["category"]),
                    "image_url": url_result["signed_url"],
                    "expires_at": url_result["expires_at"]
                })

        return {
            "success": True,
            "category": category,
            "photos": photos,
            "count": len(photos)
        }

    except Exception as e:
        logger.error(f"取得照片失敗: {e}")
        return {
            "success": False,
            "error": str(e),
            "photos": []
        }


def get_photo_title(file_name: str, category: str) -> str:
    """
    根據檔名和分類產生顯示標題

    Args:
        file_name: 照片檔名
        category: 分類

    Returns:
        顯示標題
    """
    import os

    # 移除時間戳前綴
    name = file_name

    # 嘗試移除時間戳 (格式: YYYYMMDD_HHMMSS_)
    if len(name) > 16 and name[8] == '_' and name[15] == '_':
        name = name[16:]

    # 移除副檔名
    name = os.path.splitext(name)[0]

    # 移除「拷貝」等字樣
    name = name.replace("拷貝", "").strip()

    # 如果名稱太長或不好看，用分類名稱
    if len(name) > 20 or name.startswith("_ANS") or not name:
        return CATEGORY_NAMES.get(category, "Hour Jungle 空間")

    return name


async def send_photos_to_user(
    user_id: str,
    category: str = "all",
    max_photos: int = 10
) -> Dict[str, Any]:
    """
    發送照片 Flex Message 給用戶

    Args:
        user_id: LINE 用戶 ID
        category: 分類（exterior, private_office, coworking, facilities, all）
        max_photos: 最多發送幾張照片

    Returns:
        發送結果
    """
    line_client = get_line_client()

    # 取得照片
    photos_result = await get_photos_by_category(category)

    if not photos_result.get("success") or not photos_result.get("photos"):
        logger.warning(f"沒有照片可發送 (category={category})")

        # 發送分類選單讓用戶選擇
        category_menu = build_category_menu()
        send_result = await line_client.send_flex_message(
            user_id=user_id,
            alt_text="Hour Jungle 空間照片",
            contents=category_menu
        )

        return {
            "success": send_result,
            "message": "已發送分類選單" if send_result else "發送失敗",
            "type": "category_menu"
        }

    photos = photos_result.get("photos", [])[:max_photos]

    # 建立 Carousel Flex Message
    carousel = build_photo_carousel(photos)

    # 發送照片
    alt_text = f"Hour Jungle {CATEGORY_NAMES.get(category, '空間')}照片 ({len(photos)}張)"
    send_result = await line_client.send_flex_message(
        user_id=user_id,
        alt_text=alt_text,
        contents=carousel
    )

    if send_result:
        logger.info(f"照片已發送給 {user_id}, 共 {len(photos)} 張")
        return {
            "success": True,
            "message": f"已發送 {len(photos)} 張照片",
            "type": "photo_carousel",
            "photo_count": len(photos),
            "category": category
        }
    else:
        logger.error(f"照片發送失敗: user_id={user_id}")
        return {
            "success": False,
            "error": "LINE 發送失敗",
            "type": "photo_carousel"
        }


async def send_category_menu(user_id: str) -> Dict[str, Any]:
    """
    發送分類選單給用戶

    Args:
        user_id: LINE 用戶 ID

    Returns:
        發送結果
    """
    line_client = get_line_client()

    category_menu = build_category_menu()
    send_result = await line_client.send_flex_message(
        user_id=user_id,
        alt_text="請選擇想看的空間類型",
        contents=category_menu
    )

    return {
        "success": send_result,
        "message": "已發送分類選單" if send_result else "發送失敗",
        "type": "category_menu"
    }
