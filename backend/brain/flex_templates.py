"""
Brain - LINE Flex Message 模板
定義 Hour Jungle 服務項目的 Flex Message 模板
"""

# GCS 圖片基礎路徑（需要上傳圖片到這裡）
GCS_IMAGE_BASE = "https://storage.googleapis.com/hourjungle-contracts/images"

# === 共享空間（開放座位/自由座）===
COWORKING_SPACE_FLEX = {
    "type": "bubble",
    "hero": {
        "type": "image",
        "url": f"{GCS_IMAGE_BASE}/coworking-space.jpg",
        "size": "full",
        "aspectRatio": "20:13",
        "aspectMode": "cover"
    },
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "共享空間 / 開放座位",
                "weight": "bold",
                "size": "xl"
            },
            {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "時租",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$80",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "日租",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$350",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "月租",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$3,000（月繳月使用）",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "時間",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "週一至週五 09:00~18:00",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    }
                ]
            }
        ]
    },
    "footer": {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "我想了解更多",
                    "text": "我想了解共享空間"
                },
                "color": "#22c55e"
            },
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "uri",
                    "label": "查看照片",
                    "uri": "https://drive.google.com/drive/folders/1KHIjOILKQ1OzUoWozjQhXqXv8SiSWlHE"
                }
            }
        ]
    }
}

# === 獨立辦公室 ===
PRIVATE_OFFICE_FLEX = {
    "type": "bubble",
    "hero": {
        "type": "image",
        "url": f"{GCS_IMAGE_BASE}/private-office.jpg",
        "size": "full",
        "aspectRatio": "20:13",
        "aspectMode": "cover"
    },
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "獨立辦公室（E辦公室）",
                "weight": "bold",
                "size": "xl"
            },
            {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "特色",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "對外窗、採光通風良好",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "容納",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "6~10人",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "月租",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$15,000（優惠價）",
                                "wrap": True,
                                "color": "#22c55e",
                                "size": "sm",
                                "weight": "bold",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "原價",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$18,000/月",
                                "wrap": True,
                                "color": "#999999",
                                "size": "sm",
                                "decoration": "line-through",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "押金",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$15,000",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    }
                ]
            },
            {
                "type": "text",
                "text": "✓ 獨立冷氣 ✓ 自由進出 ✓ 可自由佈置",
                "color": "#888888",
                "size": "xs",
                "margin": "md"
            }
        ]
    },
    "footer": {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "預約參觀",
                    "text": "我想預約參觀獨立辦公室"
                },
                "color": "#22c55e"
            },
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "uri",
                    "label": "查看照片",
                    "uri": "https://drive.google.com/drive/folders/1oRLXO272fblufH5m-I7OA9pglUeYTx42"
                }
            }
        ]
    }
}

# === 會議室 ===
MEETING_ROOM_FLEX = {
    "type": "bubble",
    "hero": {
        "type": "image",
        "url": f"{GCS_IMAGE_BASE}/meeting-room.jpg",
        "size": "full",
        "aspectRatio": "20:13",
        "aspectMode": "cover"
    },
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "會議室租借",
                "weight": "bold",
                "size": "xl"
            },
            {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": "📅 平日（週一至週五）",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#3b82f6"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "費用",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$380/小時（含稅）",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": "🗓 假日（週六、週日）",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#f59e0b",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "費用",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$1,650/3小時（含稅）",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "備註",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "最低起租3小時",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    }
                ]
            },
            {
                "type": "text",
                "text": "容納 8~10 人｜需提前預約",
                "color": "#888888",
                "size": "xs",
                "margin": "md"
            }
        ]
    },
    "footer": {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "我要預約會議室",
                    "text": "我要預約會議室"
                },
                "color": "#3b82f6"
            },
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "uri",
                    "label": "查看照片",
                    "uri": "https://drive.google.com/drive/folders/1N1NhEJW6nSOI1_BRNeJj5L37OZayt5Xr"
                }
            }
        ]
    }
}

# === 活動場地 ===
EVENT_SPACE_FLEX = {
    "type": "bubble",
    "hero": {
        "type": "image",
        "url": f"{GCS_IMAGE_BASE}/event-space.jpg",
        "size": "full",
        "aspectRatio": "20:13",
        "aspectMode": "cover"
    },
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "活動場地租借",
                "weight": "bold",
                "size": "xl"
            },
            {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "時間",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "僅限假日 09:00~18:00",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "費用",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$3,600/3小時（含稅）",
                                "wrap": True,
                                "color": "#22c55e",
                                "size": "sm",
                                "weight": "bold",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "人數",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "1~30人",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    }
                ]
            },
            {
                "type": "text",
                "text": "⚠️ 平日不提供場地外借",
                "color": "#f59e0b",
                "size": "xs",
                "margin": "md"
            }
        ]
    },
    "footer": {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "詢問活動場地",
                    "text": "我想詢問活動場地租借"
                },
                "color": "#22c55e"
            },
            {
                "type": "button",
                "style": "secondary",
                "height": "sm",
                "action": {
                    "type": "uri",
                    "label": "查看照片",
                    "uri": "https://drive.google.com/drive/folders/1GUTK0px_1xgNddB1B3De_AfG6ieb_sHB"
                }
            }
        ]
    }
}

# === 營業登記服務 ===
BUSINESS_REGISTRATION_FLEX = {
    "type": "bubble",
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "text",
                "text": "營業登記（借址登記）",
                "weight": "bold",
                "size": "xl"
            },
            {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": "📋 方案價格",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#22c55e"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "兩年約",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$1,490/月（半年繳）",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "一年約",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$1,800/月（年繳）",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "押金",
                                "color": "#aaaaaa",
                                "size": "sm",
                                "flex": 2
                            },
                            {
                                "type": "text",
                                "text": "$6,000",
                                "wrap": True,
                                "color": "#666666",
                                "size": "sm",
                                "flex": 5
                            }
                        ]
                    }
                ]
            },
            {
                "type": "separator",
                "margin": "lg"
            },
            {
                "type": "text",
                "text": "✓ 超過百間蝦皮店家指定選擇\n✓ 最快7天完成登記\n✓ 全額退費保證\n✓ 贈送一年免費稅務諮詢",
                "wrap": True,
                "color": "#888888",
                "size": "xs",
                "margin": "md"
            }
        ]
    },
    "footer": {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            {
                "type": "button",
                "style": "primary",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": "我想了解營業登記",
                    "text": "我想了解營業登記服務"
                },
                "color": "#22c55e"
            }
        ]
    }
}

# === 服務總覽 Carousel（輪播多張卡片）===
def get_services_carousel():
    """取得服務總覽輪播訊息（包含所有服務）"""
    return {
        "type": "carousel",
        "contents": [
            COWORKING_SPACE_FLEX,
            PRIVATE_OFFICE_FLEX,
            MEETING_ROOM_FLEX,
            EVENT_SPACE_FLEX,
            BUSINESS_REGISTRATION_FLEX
        ]
    }


# === 取得單一服務 Flex Message ===
def get_service_flex(service_type: str) -> dict:
    """
    根據服務類型取得對應的 Flex Message

    Args:
        service_type: 服務類型（coworking, office, meeting, event, registration）

    Returns:
        Flex Message dict
    """
    templates = {
        "coworking": COWORKING_SPACE_FLEX,
        "office": PRIVATE_OFFICE_FLEX,
        "meeting": MEETING_ROOM_FLEX,
        "event": EVENT_SPACE_FLEX,
        "registration": BUSINESS_REGISTRATION_FLEX
    }
    return templates.get(service_type, COWORKING_SPACE_FLEX)
