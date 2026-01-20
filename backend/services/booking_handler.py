"""
Brain - 會議室預約處理器
處理 LINE Bot 會議室預約對話流程

【型別提示說明】
- CustomerData: CRM 客戶資料
- BookingIntentType: 預約意圖類型（book/query/cancel/None）
- BookingRecord: 預約記錄
- CancelResult: 取消結果
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from services.booking_service import BookingService
from services.line_client import get_line_client
from services.crm_client import get_crm_client
from type_defs import (
    CustomerData,
    BookingIntentType,
    BookingRecord,
    CancelResult,
    TimeSlot,
)


# 預約相關關鍵字
BOOKING_KEYWORDS = [
    "預約會議室", "訂會議室", "借會議室",
    "預約會議", "訂會議", "借會議",
    "會議室預約", "會議預約",
    "我要預約", "想預約", "要預約"
]

# 查詢預約關鍵字
QUERY_KEYWORDS = ["我的預約", "查詢預約", "預約查詢", "查預約"]

# 取消預約關鍵字
CANCEL_KEYWORDS = ["取消預約"]


class BookingHandler:
    """會議室預約處理器"""

    def __init__(self):
        self.booking_service = BookingService()
        self.line_client = get_line_client()
        self.crm_client = get_crm_client()

    async def _verify_member(self, user_id: str) -> Tuple[bool, Optional[CustomerData]]:
        """
        驗證用戶是否為會員（有 active 合約）

        Args:
            user_id: LINE 用戶 ID

        Returns:
            Tuple[是否為會員, 客戶資料]
            - (True, CustomerData): 有效會員
            - (False, CustomerData): 有客戶資料但無有效合約
            - (False, None): 完全沒有客戶資料
        """
        # 查詢 CRM 客戶資料
        customer = await self.crm_client.get_customer_by_line_id(user_id)

        if not customer:
            print(f"⚠️ [Booking] 用戶 {user_id[:20]}... 不在 CRM 中")
            return False, None

        # 檢查是否有 active 合約
        contracts = customer.get("contracts", [])
        active_contracts = [c for c in contracts if c.get("contract_status") == "active"]

        if not active_contracts:
            print(f"⚠️ [Booking] 用戶 {customer.get('name')} 無有效合約")
            return False, customer

        print(f"✅ [Booking] 會員驗證通過: {customer.get('name')} (合約: {len(active_contracts)} 份)")
        return True, customer

    def is_booking_intent(self, message: str) -> Tuple[bool, BookingIntentType]:
        """
        判斷是否為預約相關意圖

        Args:
            message: 用戶訊息

        Returns:
            Tuple[是否為預約意圖, 意圖類型]
            - (True, "book"): 新預約
            - (True, "query"): 查詢預約
            - (True, "cancel"): 取消預約
            - (False, None): 非預約相關
        """
        message_lower = message.lower().strip()

        # 檢查是否為新預約
        for keyword in BOOKING_KEYWORDS:
            if keyword in message_lower:
                return True, "book"

        # 檢查是否為查詢預約
        for keyword in QUERY_KEYWORDS:
            if keyword in message_lower:
                return True, "query"

        # 檢查是否為取消預約
        for keyword in CANCEL_KEYWORDS:
            if keyword in message_lower:
                return True, "cancel"

        return False, None

    async def handle_text_message(
        self,
        db: AsyncSession,
        user_id: str,
        user_name: str,
        message: str
    ) -> Optional[bool]:
        """
        處理文字訊息中的預約意圖

        Returns:
            True: 已處理（預約相關）
            None: 非預約相關，交給其他流程處理
        """
        is_booking, intent_type = self.is_booking_intent(message)

        if not is_booking:
            return None

        if intent_type == "book":
            await self._start_booking_flow(db, user_id, user_name)
            return True
        elif intent_type == "query":
            await self._show_my_bookings(db, user_id)
            return True
        elif intent_type == "cancel":
            await self._show_cancel_options(db, user_id)
            return True

        return None

    async def handle_postback(
        self,
        db: AsyncSession,
        user_id: str,
        user_name: str,
        postback_data: str
    ) -> bool:
        """
        處理 Postback 事件

        Returns:
            True: 已處理
            False: 處理失敗
        """
        # 解析 postback data
        params = dict(p.split("=") for p in postback_data.split("&") if "=" in p)
        action = params.get("action", "")
        step = params.get("step", "")

        print(f"📅 [Booking] 處理 postback: action={action}, step={step}")

        if action == "book":
            if step == "date":
                # 選擇日期
                date = params.get("date", "")
                await self._show_time_slots(db, user_id, date)
            elif step == "time":
                # 選擇時段
                date = params.get("date", "")
                start = params.get("start", "")
                end = params.get("end", "")
                await self._confirm_booking(db, user_id, user_name, date, start, end)
            elif step == "confirm":
                # 確認預約
                date = params.get("date", "")
                start = params.get("start", "")
                end = params.get("end", "")
                await self._create_booking(db, user_id, user_name, date, start, end)

        elif action == "cancel":
            booking_id = params.get("id", "")
            if booking_id:
                await self._cancel_booking(db, user_id, int(booking_id))

        return True

    async def _start_booking_flow(self, db: AsyncSession, user_id: str, user_name: str):
        """開始預約流程 - 顯示日期選擇"""
        # === 會員驗證 ===
        is_member, customer = await self._verify_member(user_id)

        if not is_member:
            # 非會員，拒絕預約
            if customer:
                # 有客戶資料但無有效合約
                await self.line_client.send_text_message(
                    user_id,
                    f"抱歉，{customer.get('name', user_name)}，會議室預約服務僅限現有客戶使用。\n\n"
                    "您目前沒有生效中的合約。如有需要，請聯繫我們了解租賃方案：\n"
                    "📞 LINE 通話或留言給我們～"
                )
            else:
                # 完全沒有客戶資料
                await self.line_client.send_text_message(
                    user_id,
                    "抱歉，會議室預約服務僅限 Hour Jungle 現有客戶使用。\n\n"
                    "如果您對我們的服務有興趣，歡迎留言詢問！我們提供：\n"
                    "✅ 營業登記地址\n"
                    "✅ 共享辦公室\n"
                    "✅ 獨立辦公室\n\n"
                    "成為客戶後，即可免費使用會議室預約服務！"
                )
            return

        # 生成接下來 7 天的日期選項
        today = datetime.now()
        date_buttons = []

        for i in range(7):
            date = today + timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            weekday = ["一", "二", "三", "四", "五", "六", "日"][date.weekday()]

            if i == 0:
                label = f"今天 ({weekday})"
            elif i == 1:
                label = f"明天 ({weekday})"
            else:
                label = f"{date.month}/{date.day} ({weekday})"

            date_buttons.append({
                "type": "button",
                "style": "primary" if i < 3 else "secondary",
                "action": {
                    "type": "postback",
                    "label": label,
                    "data": f"action=book&step=date&date={date_str}"
                },
                "margin": "sm"
            })

        # 建立 Flex Message
        flex_contents = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "📅 會議室預約",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1DB446"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "請選擇預約日期：",
                        "margin": "md"
                    },
                    {
                        "type": "separator",
                        "margin": "lg"
                    },
                    *date_buttons
                ]
            }
        }

        await self.line_client.send_flex_message(
            user_id,
            "會議室預約 - 選擇日期",
            flex_contents
        )

    async def _show_time_slots(self, db: AsyncSession, user_id: str, date: str, room_id: int = 1):
        """顯示可用時段"""
        # 取得可用時段 (預設使用會議室 ID=1)
        available_slots = await self.booking_service.get_available_slots(db, room_id, date)

        if not available_slots:
            await self.line_client.send_text_message(
                user_id,
                f"抱歉，{date} 已沒有可預約的時段，請選擇其他日期。"
            )
            # 重新顯示日期選擇
            await self._start_booking_flow(db, user_id, "")
            return

        # 將時段分為上午和下午
        morning_slots = [s for s in available_slots if int(s["start"].split(":")[0]) < 12]
        afternoon_slots = [s for s in available_slots if int(s["start"].split(":")[0]) >= 12]

        # 建立時段按鈕
        def create_slot_buttons(slots, date):
            buttons = []
            for slot in slots[:6]:  # 最多顯示 6 個
                buttons.append({
                    "type": "button",
                    "style": "primary",
                    "action": {
                        "type": "postback",
                        "label": f"{slot['start']}~{slot['end']}",
                        "data": f"action=book&step=time&date={date}&start={slot['start']}&end={slot['end']}"
                    },
                    "height": "sm",
                    "margin": "sm"
                })
            return buttons

        morning_buttons = create_slot_buttons(morning_slots, date)
        afternoon_buttons = create_slot_buttons(afternoon_slots, date)

        # 解析日期顯示
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
        date_display = f"{date_obj.month}/{date_obj.day} ({weekday})"

        contents = []
        contents.append({
            "type": "text",
            "text": f"日期：{date_display}",
            "weight": "bold",
            "margin": "md"
        })
        contents.append({
            "type": "text",
            "text": "請選擇時段（1小時）：",
            "size": "sm",
            "color": "#888888",
            "margin": "sm"
        })
        contents.append({"type": "separator", "margin": "lg"})

        if morning_buttons:
            contents.append({
                "type": "text",
                "text": "上午",
                "weight": "bold",
                "margin": "md",
                "size": "sm"
            })
            contents.extend(morning_buttons)

        if afternoon_buttons:
            contents.append({
                "type": "text",
                "text": "下午",
                "weight": "bold",
                "margin": "lg",
                "size": "sm"
            })
            contents.extend(afternoon_buttons)

        flex_contents = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⏰ 選擇時段",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1DB446"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents
            }
        }

        await self.line_client.send_flex_message(
            user_id,
            f"會議室預約 - {date_display}",
            flex_contents
        )

    async def _confirm_booking(
        self,
        db: AsyncSession,
        user_id: str,
        user_name: str,
        date: str,
        start_time: str,
        end_time: str
    ):
        """顯示預約確認"""
        # 解析日期顯示
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
        date_display = f"{date_obj.year}/{date_obj.month}/{date_obj.day} ({weekday})"

        flex_contents = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "✅ 確認預約",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#1DB446"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "會議室", "color": "#888888", "flex": 2},
                            {"type": "text", "text": "會議室（10人）", "flex": 3}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "日期", "color": "#888888", "flex": 2},
                            {"type": "text", "text": date_display, "flex": 3}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "時段", "color": "#888888", "flex": 2},
                            {"type": "text", "text": f"{start_time} ~ {end_time}", "flex": 3}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "預約者", "color": "#888888", "flex": 2},
                            {"type": "text", "text": user_name, "flex": 3}
                        ],
                        "margin": "md"
                    },
                    {"type": "separator", "margin": "xl"},
                    {
                        "type": "text",
                        "text": "* 現有客戶免費使用",
                        "size": "xs",
                        "color": "#888888",
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "action": {
                            "type": "postback",
                            "label": "確認預約",
                            "data": f"action=book&step=confirm&date={date}&start={start_time}&end={end_time}"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "postback",
                            "label": "重新選擇",
                            "data": f"action=book&step=date&date={date}"
                        },
                        "margin": "md"
                    }
                ]
            }
        }

        await self.line_client.send_flex_message(
            user_id,
            f"確認預約 - {date_display} {start_time}~{end_time}",
            flex_contents
        )

    async def _create_booking(
        self,
        db: AsyncSession,
        user_id: str,
        user_name: str,
        date: str,
        start_time: str,
        end_time: str,
        room_id: int = 1
    ):
        """建立預約"""
        booking, message = await self.booking_service.create_booking(
            db=db,
            room_id=room_id,  # 預設使用會議室 ID=1
            customer_line_id=user_id,
            customer_name=user_name,
            date=date,
            start_time=start_time,
            end_time=end_time
        )

        if booking:
            booking_number = booking.booking_number

            # 解析日期顯示
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
            date_display = f"{date_obj.year}/{date_obj.month}/{date_obj.day} ({weekday})"

            flex_contents = {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#1DB446",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🎉 預約成功！",
                            "weight": "bold",
                            "size": "xl",
                            "color": "#FFFFFF"
                        }
                    ],
                    "paddingAll": "lg"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"預約編號：{booking_number}",
                            "weight": "bold",
                            "margin": "md"
                        },
                        {"type": "separator", "margin": "lg"},
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "會議室", "color": "#888888", "flex": 2},
                                {"type": "text", "text": "會議室（10人）", "flex": 3}
                            ],
                            "margin": "lg"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "日期", "color": "#888888", "flex": 2},
                                {"type": "text", "text": date_display, "flex": 3}
                            ],
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "時段", "color": "#888888", "flex": 2},
                                {"type": "text", "text": f"{start_time} ~ {end_time}", "flex": 3}
                            ],
                            "margin": "md"
                        },
                        {"type": "separator", "margin": "xl"},
                        {
                            "type": "text",
                            "text": "會議開始前 1 小時會發送提醒通知",
                            "size": "xs",
                            "color": "#888888",
                            "margin": "md",
                            "wrap": True
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                                "type": "postback",
                                "label": "查看我的預約",
                                "data": "action=book&step=list"
                            }
                        }
                    ]
                }
            }

            await self.line_client.send_flex_message(
                user_id,
                f"預約成功 - {booking_number}",
                flex_contents
            )
        else:
            error_msg = message or "預約失敗，請稍後再試"
            await self.line_client.send_text_message(
                user_id,
                f"❌ {error_msg}\n\n請重新選擇時段，或聯繫客服協助。"
            )

    async def _show_my_bookings(self, db: AsyncSession, user_id: str) -> None:
        """
        顯示我的預約

        Args:
            db: 資料庫 Session
            user_id: LINE 用戶 ID
        """
        bookings: List[BookingRecord] = await self.booking_service.get_customer_bookings(db, user_id)

        if not bookings:
            await self.line_client.send_text_message(
                user_id,
                "您目前沒有預約記錄。\n\n輸入「預約會議室」開始預約！"
            )
            return

        # 建立預約列表
        booking_bubbles = []
        for booking in bookings[:5]:  # 最多顯示 5 筆
            date_obj = datetime.strptime(booking["date"], "%Y-%m-%d")
            weekday = ["一", "二", "三", "四", "五", "六", "日"][date_obj.weekday()]
            date_display = f"{date_obj.month}/{date_obj.day} ({weekday})"

            status_text = "✅ 已確認" if booking["status"] == "confirmed" else "❌ 已取消"

            bubble = {
                "type": "bubble",
                "size": "kilo",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": booking["booking_number"],
                            "weight": "bold",
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": f"{date_display} {booking['start_time']}~{booking['end_time']}",
                            "margin": "sm"
                        },
                        {
                            "type": "text",
                            "text": status_text,
                            "size": "sm",
                            "color": "#1DB446" if booking["status"] == "confirmed" else "#FF5555",
                            "margin": "sm"
                        }
                    ]
                }
            }

            # 如果是已確認狀態，加入取消按鈕
            if booking["status"] == "confirmed":
                bubble["footer"] = {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                                "type": "postback",
                                "label": "取消預約",
                                "data": f"action=cancel&id={booking['id']}"
                            },
                            "height": "sm"
                        }
                    ]
                }

            booking_bubbles.append(bubble)

        flex_contents = {
            "type": "carousel",
            "contents": booking_bubbles
        }

        await self.line_client.send_flex_message(
            user_id,
            "我的會議室預約",
            flex_contents
        )

    async def _show_cancel_options(self, db: AsyncSession, user_id: str):
        """顯示可取消的預約"""
        await self._show_my_bookings(db, user_id)

    async def _cancel_booking(self, db: AsyncSession, user_id: str, booking_id: int) -> None:
        """
        取消預約

        Args:
            db: 資料庫 Session
            user_id: LINE 用戶 ID
            booking_id: 預約 ID
        """
        result: CancelResult = await self.booking_service.cancel_booking(
            db=db,
            booking_id=booking_id,
            reason="客戶自行取消"
        )

        if result.get("success"):
            await self.line_client.send_text_message(
                user_id,
                "✅ 預約已取消\n\n如需重新預約，請輸入「預約會議室」"
            )
        else:
            error_msg = result.get("error", "取消失敗")
            await self.line_client.send_text_message(
                user_id,
                f"❌ {error_msg}"
            )


# 全域實例
_booking_handler: Optional[BookingHandler] = None


def get_booking_handler() -> BookingHandler:
    """取得預約處理器單例"""
    global _booking_handler
    if _booking_handler is None:
        _booking_handler = BookingHandler()
    return _booking_handler
