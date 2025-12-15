"""
Brain - 會議室預約服務
處理會議室預約的所有業務邏輯
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from db.models import MeetingRoom, MeetingRoomBooking
from services.google_calendar import get_calendar_service


class BookingService:
    """會議室預約服務"""

    # 營業時間
    BUSINESS_HOURS_START = "09:00"
    BUSINESS_HOURS_END = "18:00"
    TIME_SLOT_MINUTES = 30  # 最小預約單位

    def __init__(self):
        self.calendar_service = get_calendar_service()

    async def get_rooms(self, db: AsyncSession) -> List[Dict]:
        """
        取得所有會議室列表

        Returns:
            會議室列表
        """
        result = await db.execute(
            select(MeetingRoom).where(MeetingRoom.is_active == True)
        )
        rooms = result.scalars().all()

        return [
            {
                "id": room.id,
                "name": room.name,
                "capacity": room.capacity,
                "amenities": room.amenities or [],
                "hourly_rate": room.hourly_rate
            }
            for room in rooms
        ]

    async def get_available_slots(
        self,
        db: AsyncSession,
        room_id: int,
        date: str
    ) -> List[Dict]:
        """
        取得指定日期的可用時段

        Args:
            db: 資料庫連線
            room_id: 會議室 ID
            date: 日期 (YYYY-MM-DD)

        Returns:
            可用時段列表 [{"start": "09:00", "end": "09:30", "available": True}, ...]
        """
        # 取得會議室資訊
        result = await db.execute(
            select(MeetingRoom).where(MeetingRoom.id == room_id)
        )
        room = result.scalar_one_or_none()
        if not room:
            return []

        # 產生所有時段
        all_slots = self._generate_time_slots()

        # 從資料庫取得已預約時段
        db_bookings = await db.execute(
            select(MeetingRoomBooking).where(
                and_(
                    MeetingRoomBooking.meeting_room_id == room_id,
                    MeetingRoomBooking.booking_date == date,
                    MeetingRoomBooking.status == "confirmed"
                )
            )
        )
        booked_from_db = db_bookings.scalars().all()

        # 從 Google Calendar 取得忙碌時段
        busy_from_calendar = []
        if room.google_calendar_id and self.calendar_service.is_available():
            busy_from_calendar = await self.calendar_service.get_busy_times(
                room.google_calendar_id,
                date
            )

        # 合併所有已佔用時段
        busy_times = []

        # 資料庫的預約
        for booking in booked_from_db:
            busy_times.append({
                "start": booking.start_time,
                "end": booking.end_time
            })

        # 日曆的事件
        for event in busy_from_calendar:
            busy_times.append({
                "start": event["start"],
                "end": event["end"]
            })

        # 標記可用性
        available_slots = []
        for slot in all_slots:
            is_available = not self._is_time_overlap(
                slot["start"], slot["end"], busy_times
            )
            available_slots.append({
                "start": slot["start"],
                "end": slot["end"],
                "available": is_available
            })

        return available_slots

    async def check_availability(
        self,
        db: AsyncSession,
        room_id: int,
        date: str,
        start_time: str,
        end_time: str
    ) -> Tuple[bool, str]:
        """
        檢查指定時段是否可用

        Returns:
            (是否可用, 原因訊息)
        """
        # 驗證時間格式
        if not self._validate_time_range(start_time, end_time):
            return False, "時間範圍無效"

        # 驗證營業時間
        if start_time < self.BUSINESS_HOURS_START or end_time > self.BUSINESS_HOURS_END:
            return False, f"營業時間為 {self.BUSINESS_HOURS_START} ~ {self.BUSINESS_HOURS_END}"

        # 取得可用時段
        slots = await self.get_available_slots(db, room_id, date)

        # 檢查所需時段是否都可用
        for slot in slots:
            if slot["start"] >= start_time and slot["end"] <= end_time:
                if not slot["available"]:
                    return False, f"{slot['start']} ~ {slot['end']} 已被預約"

        return True, "可預約"

    async def create_booking(
        self,
        db: AsyncSession,
        room_id: int,
        customer_line_id: str,
        customer_name: str,
        date: str,
        start_time: str,
        end_time: str,
        purpose: str = None,
        attendees_count: int = None,
        notes: str = None
    ) -> Tuple[Optional[MeetingRoomBooking], str]:
        """
        建立預約

        Returns:
            (預約記錄, 訊息)
        """
        # 檢查可用性
        is_available, reason = await self.check_availability(
            db, room_id, date, start_time, end_time
        )
        if not is_available:
            return None, reason

        # 取得會議室
        result = await db.execute(
            select(MeetingRoom).where(MeetingRoom.id == room_id)
        )
        room = result.scalar_one_or_none()
        if not room:
            return None, "會議室不存在"

        # 產生預約編號
        booking_number = await self._generate_booking_number(db, date)

        # 計算時長
        duration = self._calculate_duration(start_time, end_time)

        # 建立預約記錄
        booking = MeetingRoomBooking(
            booking_number=booking_number,
            meeting_room_id=room_id,
            customer_line_id=customer_line_id,
            customer_name=customer_name,
            booking_date=date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            purpose=purpose,
            attendees_count=attendees_count,
            notes=notes,
            status="confirmed",
            created_by="line"
        )

        # 同步到 Google Calendar
        if room.google_calendar_id and self.calendar_service.is_available():
            event_id = await self.calendar_service.create_event(
                calendar_id=room.google_calendar_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                summary=f"會議室預約 - {customer_name}",
                description=f"預約編號: {booking_number}\n人數: {attendees_count or '未指定'}\n目的: {purpose or '未指定'}"
            )
            booking.google_event_id = event_id

        db.add(booking)
        await db.commit()
        await db.refresh(booking)

        return booking, "預約成功"

    async def cancel_booking(
        self,
        db: AsyncSession,
        booking_id: int,
        reason: str = None
    ) -> Tuple[bool, str]:
        """
        取消預約

        Returns:
            (是否成功, 訊息)
        """
        result = await db.execute(
            select(MeetingRoomBooking).where(MeetingRoomBooking.id == booking_id)
        )
        booking = result.scalar_one_or_none()

        if not booking:
            return False, "找不到預約記錄"

        if booking.status == "cancelled":
            return False, "此預約已取消"

        # 從 Google Calendar 刪除
        if booking.google_event_id:
            room_result = await db.execute(
                select(MeetingRoom).where(MeetingRoom.id == booking.meeting_room_id)
            )
            room = room_result.scalar_one_or_none()
            if room and room.google_calendar_id:
                await self.calendar_service.delete_event(
                    room.google_calendar_id,
                    booking.google_event_id
                )

        # 更新狀態
        booking.status = "cancelled"
        booking.cancelled_at = datetime.utcnow()
        booking.cancel_reason = reason

        await db.commit()
        return True, "預約已取消"

    async def get_customer_bookings(
        self,
        db: AsyncSession,
        customer_line_id: str,
        include_past: bool = False
    ) -> List[Dict]:
        """
        取得客戶的預約列表

        Returns:
            預約列表
        """
        today = datetime.now().strftime("%Y-%m-%d")

        query = select(MeetingRoomBooking).where(
            MeetingRoomBooking.customer_line_id == customer_line_id
        )

        if not include_past:
            query = query.where(MeetingRoomBooking.booking_date >= today)

        query = query.order_by(MeetingRoomBooking.booking_date, MeetingRoomBooking.start_time)

        result = await db.execute(query)
        bookings = result.scalars().all()

        booking_list = []
        for booking in bookings:
            # 取得會議室名稱
            room_result = await db.execute(
                select(MeetingRoom).where(MeetingRoom.id == booking.meeting_room_id)
            )
            room = room_result.scalar_one_or_none()

            booking_list.append({
                "id": booking.id,
                "booking_number": booking.booking_number,
                "room_name": room.name if room else "未知",
                "date": booking.booking_date,
                "start_time": booking.start_time,
                "end_time": booking.end_time,
                "duration_minutes": booking.duration_minutes,
                "status": booking.status,
                "purpose": booking.purpose
            })

        return booking_list

    async def format_booking_confirmation(
        self,
        booking: MeetingRoomBooking,
        room: MeetingRoom
    ) -> str:
        """格式化預約確認訊息"""
        # 計算費用（目前免費）
        hours = booking.duration_minutes / 60
        cost = int(hours * room.hourly_rate / 100) if room.hourly_rate else 0

        msg = f"""✅ 預約成功！

📋 預約編號：{booking.booking_number}
🏢 會議室：{room.name}（{room.capacity}人）
📅 日期：{booking.booking_date}
⏰ 時間：{booking.start_time} ~ {booking.end_time}
⏱️ 時長：{booking.duration_minutes} 分鐘"""

        if cost > 0:
            msg += f"\n💰 費用：${cost}"
        else:
            msg += f"\n💰 費用：免費（現有客戶福利）"

        msg += """

📍 地點：台中市西區大忠南街55號7F-5
🔔 我們會在預約前 1 小時提醒您

如需取消或修改，請回覆「取消預約」或「修改預約」"""

        return msg

    def _generate_time_slots(self) -> List[Dict]:
        """產生所有時段"""
        slots = []
        current = datetime.strptime(self.BUSINESS_HOURS_START, "%H:%M")
        end = datetime.strptime(self.BUSINESS_HOURS_END, "%H:%M")

        while current < end:
            next_time = current + timedelta(minutes=self.TIME_SLOT_MINUTES)
            slots.append({
                "start": current.strftime("%H:%M"),
                "end": next_time.strftime("%H:%M")
            })
            current = next_time

        return slots

    def _is_time_overlap(
        self,
        start: str,
        end: str,
        busy_times: List[Dict]
    ) -> bool:
        """檢查時段是否與忙碌時段重疊"""
        for busy in busy_times:
            # 檢查重疊：not (end <= busy_start or start >= busy_end)
            if not (end <= busy["start"] or start >= busy["end"]):
                return True
        return False

    def _validate_time_range(self, start: str, end: str) -> bool:
        """驗證時間範圍"""
        try:
            start_dt = datetime.strptime(start, "%H:%M")
            end_dt = datetime.strptime(end, "%H:%M")
            return end_dt > start_dt
        except ValueError:
            return False

    def _calculate_duration(self, start: str, end: str) -> int:
        """計算時長（分鐘）"""
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = datetime.strptime(end, "%H:%M")
        return int((end_dt - start_dt).total_seconds() / 60)

    async def _generate_booking_number(self, db: AsyncSession, date: str) -> str:
        """產生預約編號"""
        date_str = date.replace("-", "")

        # 查詢當天已有幾筆預約
        result = await db.execute(
            select(MeetingRoomBooking).where(
                MeetingRoomBooking.booking_number.like(f"MR-{date_str}-%")
            )
        )
        count = len(result.scalars().all())

        return f"MR-{date_str}-{count + 1:04d}"


# 全域實例
_booking_service: Optional[BookingService] = None


def get_booking_service() -> BookingService:
    """取得預約服務單例"""
    global _booking_service
    if _booking_service is None:
        _booking_service = BookingService()
    return _booking_service
