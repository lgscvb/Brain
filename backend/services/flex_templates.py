"""
Brain - LINE Flex Message 模板
建立照片展示用的 Flex Message

Flex Message 限制：
- Carousel 最多 12 個 bubble
- 圖片 URL 必須是 HTTPS
- 圖片建議比例 1.51:1 或 4:3
"""

from typing import List, Dict, Any


# 分類中文名稱
CATEGORY_NAMES = {
    "exterior": "大樓外觀",
    "private_office": "獨立辦公室",
    "coworking": "共享空間",
    "facilities": "設施",
    "other": "其他",
    "all": "所有照片",
}

# 分類顏色
CATEGORY_COLORS = {
    "exterior": "#4A90D9",      # 藍色
    "private_office": "#50C878", # 綠色
    "coworking": "#FF9F43",      # 橘色
    "facilities": "#9B59B6",     # 紫色
    "other": "#95A5A6",          # 灰色
}


def build_photo_bubble(
    image_url: str,
    title: str,
    category: str,
    index: int = None,
    total: int = None
) -> Dict[str, Any]:
    """
    建立單張照片的 Bubble

    Args:
        image_url: 照片 URL（簽名 URL）
        title: 照片標題
        category: 分類
        index: 照片索引（用於顯示 1/10）
        total: 總照片數

    Returns:
        Bubble JSON
    """
    category_name = CATEGORY_NAMES.get(category, "Hour Jungle")
    category_color = CATEGORY_COLORS.get(category, "#888888")

    # 標題文字
    title_text = title if title else category_name

    # 副標題（顯示分類和索引）
    subtitle_parts = [category_name]
    if index is not None and total is not None:
        subtitle_parts.append(f"{index}/{total}")
    subtitle_text = " · ".join(subtitle_parts)

    return {
        "type": "bubble",
        "size": "kilo",
        "hero": {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "4:3",
            "aspectMode": "cover"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title_text,
                    "weight": "bold",
                    "size": "md",
                    "wrap": True,
                    "maxLines": 2
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "baseline",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": subtitle_text,
                                    "size": "xs",
                                    "color": category_color,
                                    "flex": 0
                                }
                            ]
                        }
                    ],
                    "margin": "md"
                }
            ],
            "spacing": "sm",
            "paddingAll": "13px"
        }
    }


def build_photo_carousel(
    photos: List[Dict[str, Any]],
    max_photos: int = 10
) -> Dict[str, Any]:
    """
    建立照片 Carousel Flex Message

    Args:
        photos: 照片列表，每個元素包含:
            - image_url: 簽名 URL
            - title: 標題
            - category: 分類
        max_photos: 最多顯示幾張照片（LINE 限制 12）

    Returns:
        Carousel Flex Message JSON
    """
    # LINE Carousel 最多 12 個 bubble，但我們預留一些空間
    photos = photos[:min(max_photos, 12)]

    if not photos:
        return build_no_photos_message()

    total = len(photos)
    bubbles = []

    for i, photo in enumerate(photos, 1):
        bubble = build_photo_bubble(
            image_url=photo.get("image_url", ""),
            title=photo.get("title", ""),
            category=photo.get("category", "other"),
            index=i,
            total=total
        )
        bubbles.append(bubble)

    return {
        "type": "carousel",
        "contents": bubbles
    }


def build_category_menu() -> Dict[str, Any]:
    """
    建立分類選單 Flex Message

    Returns:
        Flex Message JSON（讓用戶選擇要看哪種照片）
    """
    categories = [
        ("exterior", "大樓外觀", "🏢"),
        ("private_office", "獨立辦公室", "🚪"),
        ("coworking", "共享空間", "💼"),
        ("facilities", "設施環境", "🛠"),
        ("all", "全部照片", "📷"),
    ]

    buttons = []
    for cat_key, cat_name, emoji in categories:
        buttons.append({
            "type": "button",
            "action": {
                "type": "postback",
                "label": f"{emoji} {cat_name}",
                "data": f"action=view_photos&category={cat_key}"
            },
            "style": "secondary",
            "height": "sm",
            "margin": "sm"
        })

    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "Hour Jungle 空間照片",
                    "weight": "bold",
                    "size": "lg",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "請選擇想看的空間類型",
                    "size": "sm",
                    "color": "#888888",
                    "margin": "md"
                },
                {
                    "type": "separator",
                    "margin": "lg"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "sm",
                    "contents": buttons
                }
            ]
        }
    }


def build_no_photos_message() -> Dict[str, Any]:
    """
    建立無照片訊息

    Returns:
        Flex Message JSON
    """
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📷",
                    "size": "xxl",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": "暫無照片",
                    "weight": "bold",
                    "size": "lg",
                    "align": "center",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "此分類目前沒有照片",
                    "size": "sm",
                    "color": "#888888",
                    "align": "center",
                    "margin": "md"
                }
            ],
            "paddingAll": "20px"
        }
    }


def build_photo_intro_message(category: str = "all") -> Dict[str, Any]:
    """
    建立照片介紹訊息（發送照片前的引言）

    Args:
        category: 分類

    Returns:
        Flex Message JSON
    """
    category_name = CATEGORY_NAMES.get(category, "Hour Jungle 空間")

    intro_texts = {
        "exterior": "這是我們位於台中市西區的大樓外觀～",
        "private_office": "這是我們的獨立辦公室，可依需求選擇不同大小～",
        "coworking": "這是我們的共享空間，舒適的工作環境～",
        "facilities": "這是我們的設施設備，乾淨整潔～",
        "all": "這是我們 Hour Jungle 的空間照片，歡迎參觀～",
    }

    intro_text = intro_texts.get(category, "這是我們的空間照片～")

    return {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📷 {category_name}",
                    "weight": "bold",
                    "size": "md"
                },
                {
                    "type": "text",
                    "text": intro_text,
                    "size": "sm",
                    "color": "#666666",
                    "margin": "md",
                    "wrap": True
                }
            ],
            "paddingAll": "15px"
        }
    }
