"""
Brain - 會議室預約 API 路由
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.database import get_db
from db.models import MeetingRoom, MeetingRoomBooking
from services.booking_service import get_booking_service


router = APIRouter()


# === Request/Response Models ===

class BookingRequest(BaseModel):
    """預約請求"""
    room_id: int
    customer_line_id: str
    customer_name: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    purpose: Optional[str] = None
    attendees_count: Optional[int] = None
    notes: Optional[str] = None


class CancelRequest(BaseModel):
    """取消請求"""
    reason: Optional[str] = None


# === API Routes ===

@router.get("/rooms")
async def list_rooms(db: AsyncSession = Depends(get_db)):
    """取得會議室列表"""
    booking_service = get_booking_service()
    rooms = await booking_service.get_rooms(db)
    return {"rooms": rooms}


@router.get("/rooms/{room_id}/availability")
async def get_availability(
    room_id: int,
    date: str,
    db: AsyncSession = Depends(get_db)
):
    """
    取得指定日期的可用時段

    Args:
        room_id: 會議室 ID
        date: 日期 (YYYY-MM-DD)
    """
    booking_service = get_booking_service()
    slots = await booking_service.get_available_slots(db, room_id, date)

    if not slots:
        raise HTTPException(status_code=404, detail="會議室不存在")

    return {
        "room_id": room_id,
        "date": date,
        "slots": slots
    }


@router.post("/bookings")
async def create_booking(
    request: BookingRequest,
    db: AsyncSession = Depends(get_db)
):
    """建立預約"""
    booking_service = get_booking_service()

    booking, message = await booking_service.create_booking(
        db=db,
        room_id=request.room_id,
        customer_line_id=request.customer_line_id,
        customer_name=request.customer_name,
        date=request.date,
        start_time=request.start_time,
        end_time=request.end_time,
        purpose=request.purpose,
        attendees_count=request.attendees_count,
        notes=request.notes
    )

    if not booking:
        raise HTTPException(status_code=400, detail=message)

    # 取得會議室資訊
    room_result = await db.execute(
        select(MeetingRoom).where(MeetingRoom.id == request.room_id)
    )
    room = room_result.scalar_one_or_none()

    # 格式化確認訊息
    confirmation = await booking_service.format_booking_confirmation(booking, room)

    return {
        "success": True,
        "message": message,
        "booking": {
            "id": booking.id,
            "booking_number": booking.booking_number,
            "room_name": room.name if room else "未知",
            "date": booking.booking_date,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "duration_minutes": booking.duration_minutes,
            "status": booking.status
        },
        "confirmation_message": confirmation
    }


@router.delete("/bookings/{booking_id}")
async def cancel_booking(
    booking_id: int,
    request: CancelRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """取消預約"""
    booking_service = get_booking_service()

    reason = request.reason if request else None
    success, message = await booking_service.cancel_booking(db, booking_id, reason)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"success": True, "message": message}


@router.get("/bookings/customer/{customer_line_id}")
async def get_customer_bookings(
    customer_line_id: str,
    include_past: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """取得客戶的預約列表"""
    booking_service = get_booking_service()
    bookings = await booking_service.get_customer_bookings(
        db, customer_line_id, include_past
    )

    return {"bookings": bookings}


@router.get("/bookings")
async def list_bookings(
    date: Optional[str] = None,
    room_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    列出預約（管理用）

    Args:
        date: 篩選日期 (YYYY-MM-DD)
        room_id: 篩選會議室
        status: 篩選狀態 (confirmed, cancelled, completed)
        limit: 返回數量限制
    """
    query = select(MeetingRoomBooking)

    if date:
        query = query.where(MeetingRoomBooking.booking_date == date)
    if room_id:
        query = query.where(MeetingRoomBooking.meeting_room_id == room_id)
    if status:
        query = query.where(MeetingRoomBooking.status == status)

    query = query.order_by(
        MeetingRoomBooking.booking_date.desc(),
        MeetingRoomBooking.start_time
    ).limit(limit)

    result = await db.execute(query)
    bookings = result.scalars().all()

    booking_list = []
    for booking in bookings:
        room_result = await db.execute(
            select(MeetingRoom).where(MeetingRoom.id == booking.meeting_room_id)
        )
        room = room_result.scalar_one_or_none()

        booking_list.append({
            "id": booking.id,
            "booking_number": booking.booking_number,
            "room_name": room.name if room else "未知",
            "customer_name": booking.customer_name,
            "date": booking.booking_date,
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "duration_minutes": booking.duration_minutes,
            "status": booking.status,
            "purpose": booking.purpose,
            "created_at": booking.created_at.isoformat() if booking.created_at else None
        })

    return {"bookings": booking_list}


# === 初始化會議室（只執行一次）===

@router.post("/rooms/init")
async def init_rooms(db: AsyncSession = Depends(get_db)):
    """
    初始化會議室資料（首次設定用）
    """
    # 檢查是否已有會議室
    result = await db.execute(select(MeetingRoom))
    existing = result.scalars().all()

    if existing:
        return {"message": "會議室已存在", "rooms": len(existing)}

    # 建立預設會議室
    room = MeetingRoom(
        name="會議室",
        capacity=10,
        hourly_rate=0,  # 免費
        amenities=["投影機", "白板", "電視螢幕"],
        google_calendar_id=None,  # 稍後設定
        is_active=True
    )

    db.add(room)
    await db.commit()

    return {"message": "會議室已建立", "room_id": room.id}


@router.put("/rooms/{room_id}/calendar")
async def set_room_calendar(
    room_id: int,
    calendar_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    設定會議室的 Google Calendar ID
    """
    result = await db.execute(
        select(MeetingRoom).where(MeetingRoom.id == room_id)
    )
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=404, detail="會議室不存在")

    room.google_calendar_id = calendar_id
    await db.commit()

    return {"message": "Calendar ID 已更新", "room_id": room_id}
