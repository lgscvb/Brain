"""
Brain - Webhook API 路由
處理 LINE Webhook 事件

架構說明：
1. LINE 訊息進入 Brain
2. 訊息存入 DB，觸發草稿生成 (draft_generator.py)
3. draft_generator 使用 LLM 生成草稿時自動判斷意圖
4. 如果 LLM 判斷是「預約會議室」→ 自動轉發 MCP 處理
5. 如果是其他意圖 → 正常草稿流程

注意：預約相關的 Postback 事件需直接轉發到 MCP
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import Message
from brain.draft_generator import get_draft_generator
from services.line_client import get_line_client
from services.jungle_client import get_jungle_client
from services.rate_limiter import get_rate_limiter
from services.booking_handler import get_booking_handler
from config import settings


router = APIRouter()


@router.post("/webhook/line")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    LINE Webhook 端點

    接收 LINE 訊息事件並處理
    """
    # 取得 Body 和 Signature
    body = await request.body()
    body_str = body.decode('utf-8')
    signature = request.headers.get('X-Line-Signature', '')

    # 驗證簽名
    line_client = get_line_client()
    if not line_client.verify_signature(body_str, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 解析事件
    import json
    try:
        events = json.loads(body_str).get('events', [])
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 取得 booking_handler 處理會議室預約
    booking_handler = get_booking_handler()

    # 處理每個事件
    for event in events:
        event_type = event.get('type')
        user_id = event.get('source', {}).get('userId', '')

        if not user_id:
            continue

        # 取得用戶資料（預約需要用到）
        line_client = get_line_client()
        user_profile = await line_client.get_user_profile(user_id)
        user_name = user_profile.get('display_name', '未知用戶') if user_profile else '未知用戶'

        # === 處理 Postback 事件（會議室預約流程使用）===
        if event_type == 'postback':
            postback_data = event.get('postback', {}).get('data', '')

            # 檢查是否為預約相關的 postback
            if postback_data.startswith('action=book') or postback_data.startswith('action=cancel'):
                print(f"📅 [Booking] 處理 postback: {postback_data[:50]}...")

                # 使用 booking_handler 處理
                await booking_handler.handle_postback(
                    db=db,
                    user_id=user_id,
                    user_name=user_name,
                    postback_data=postback_data
                )

                print(f"✅ [Booking] Postback 處理完成")
                continue  # 跳過後續處理

        # === 處理文字訊息 ===
        if event_type == 'message' and event.get('message', {}).get('type') == 'text':
            message_text = event.get('message', {}).get('text', '')

            if not message_text:
                continue

            print(f"📝 [Brain] 處理訊息: '{message_text[:30]}...'")

            # === 會議室預約意圖檢測（優先處理）===
            is_booking, booking_type = booking_handler.is_booking_intent(message_text)
            if is_booking:
                print(f"📅 [Booking] 檢測到預約意圖: {booking_type}")
                await booking_handler.handle_text_message(
                    db=db,
                    user_id=user_id,
                    user_name=user_name,
                    message=message_text
                )
                continue  # 預約訊息不進入草稿生成流程

            # === 防洗頻檢查 ===
            if settings.ENABLE_RATE_LIMIT:
                rate_limiter = get_rate_limiter()
                is_allowed, reason = rate_limiter.check_rate_limit(user_id, message_text)

                if not is_allowed:
                    print(f"🚫 訊息被攔截 (user: {user_id[:20]}...): {reason}")

                    # 可選：回覆用戶被限制的訊息
                    if reason.startswith("cooldown:"):
                        remaining = reason.split(":")[1]
                        await line_client.reply_message(
                            user_id,
                            f"您發送訊息過於頻繁，請稍後 {remaining} 再試。"
                        )
                    elif reason.startswith("rate_limit:"):
                        await line_client.reply_message(
                            user_id,
                            "您發送訊息過於頻繁，請稍後再試。"
                        )
                    elif reason.startswith("duplicate:"):
                        await line_client.reply_message(
                            user_id,
                            "請勿重複發送相同訊息。"
                        )
                    elif reason.startswith("blocked:"):
                        # 黑名單用戶不回覆
                        pass

                    continue  # 跳過此訊息，不生成草稿

            # 建立訊息記錄（使用前面取得的 user_name）
            message = Message(
                source="line_oa",
                sender_id=user_id,
                sender_name=user_name,
                content=message_text,
                status="pending",
                priority="medium"
            )

            db.add(message)
            await db.commit()
            await db.refresh(message)

            # 背景生成草稿（使用獨立 Session）
            async def generate_draft_task():
                from db.database import AsyncSessionLocal
                from db.models import Draft
                from config import settings
                from sqlalchemy import select

                async with AsyncSessionLocal() as task_db:
                    draft_generator = get_draft_generator()
                    try:
                        # 生成草稿（包含對話上下文）
                        await draft_generator.generate(
                            db=task_db,
                            message_id=message.id,
                            content=message.content,
                            sender_name=message.sender_name,
                            source=message.source,
                            sender_id=message.sender_id  # 用於取得對話歷史
                        )

                        # 如果是自動回覆模式，直接發送第一個草稿
                        if settings.AUTO_REPLY_MODE:
                            # 查詢剛生成的草稿
                            result = await task_db.execute(
                                select(Draft)
                                .where(Draft.message_id == message.id)
                                .order_by(Draft.created_at.asc())
                                .limit(1)
                            )
                            first_draft = result.scalar_one_or_none()

                            if first_draft:
                                # 發送到 LINE
                                await line_client.reply_message(
                                    user_id,
                                    first_draft.content
                                )

                                # 更新訊息狀態為已發送
                                msg_result = await task_db.execute(
                                    select(Message).where(Message.id == message.id)
                                )
                                msg = msg_result.scalar_one_or_none()
                                if msg:
                                    msg.status = "sent"
                                    await task_db.commit()

                                print(f"✅ 自動模式：已發送草稿給 {user_name}")

                    except Exception as e:
                        print(f"背景草稿生成/發送失敗: {str(e)}")

            background_tasks.add_task(generate_draft_task)

    # LINE 要求回傳 200
    return {"status": "ok"}
