"""
Brain - Webhook API 路由
處理 LINE Webhook 事件

架構說明：
1. LINE 訊息進入 Brain
2. 使用 LLM Routing 判斷意圖（包含「預約會議室」意圖）
3. 如果 LLM 判斷是「BOOKING」→ 轉發到 MCP Server（MCP 的 LLM 有 booking tools）
4. 如果是其他意圖 → 正常草稿生成流程

注意：預約相關的 Postback 事件也轉發到 MCP Server 處理
"""
import logging
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import Message
from brain.draft_generator import get_draft_generator
from services.line_client import get_line_client
from services.crm_client import get_crm_client
from services.rate_limiter import get_rate_limiter
from services.claude_client import get_claude_client
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
                logger.info(f"[Booking] 處理 postback: {postback_data[:50]}...")

                # 轉發到 MCP Server 處理（MCP Server 的 LLM 有 booking tools）
                crm_client = get_crm_client()
                forward_result = await crm_client.forward_line_event(
                    user_id=user_id,
                    message_text="",  # postback 沒有文字
                    event_type="postback",
                    postback_data=postback_data
                )

                if forward_result.get("success"):
                    logger.info("[Booking] Postback 已轉發到 MCP Server")
                else:
                    logger.warning(f"[Booking] Postback 轉發失敗: {forward_result.get('error')}")

                continue  # 跳過後續處理

        # === 處理文字訊息 ===
        if event_type == 'message' and event.get('message', {}).get('type') == 'text':
            message_text = event.get('message', {}).get('text', '')

            if not message_text:
                continue

            logger.info(f"[Brain] 處理訊息: '{message_text[:30]}...'")

            # === 防洗頻檢查（放在 LLM routing 之前，節省 API 費用）===
            if settings.ENABLE_RATE_LIMIT:
                rate_limiter = get_rate_limiter()
                is_allowed, reason = rate_limiter.check_rate_limit(user_id, message_text)

                if not is_allowed:
                    logger.info(f"訊息被攔截 (user: {user_id[:20]}...): {reason}")

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

            # === LLM Routing 意圖判斷 ===
            claude_client = get_claude_client()
            routing_result = await claude_client.route_task(message_text)
            complexity = routing_result.get("complexity", "COMPLEX")
            suggested_intent = routing_result.get("suggested_intent", "其他")

            logger.debug(f"[Routing] complexity={complexity}, intent={suggested_intent}")

            # === BOOKING 意圖 → 先檢查會員身份 ===
            if complexity == "BOOKING":
                logger.info("[Booking] LLM 判斷為預約意圖，檢查會員身份")

                # 檢查是否為會員（有 active 合約）
                crm_client = get_crm_client()
                customer = await crm_client.get_customer_by_line_id(user_id)

                is_member = False
                if customer:
                    contracts = customer.get("contracts", [])
                    active_contracts = [c for c in contracts if c.get("contract_status") == "active"]
                    is_member = len(active_contracts) > 0
                    logger.debug(f"[Booking] 客戶: {customer.get('name')}, 有效合約: {len(active_contracts)}")
                else:
                    logger.debug("[Booking] 非 CRM 客戶")

                if is_member:
                    # === 會員 → 轉發到 MCP Server 自助預約 ===
                    logger.info("[Booking] 會員，轉發到 MCP Server 自助預約")

                    # 記錄訊息到 Brain（狀態為 booking）
                    booking_message = Message(
                        source="line_oa",
                        sender_id=user_id,
                        sender_name=user_name,
                        content=message_text,
                        status="booking",
                        priority="low"
                    )
                    db.add(booking_message)
                    await db.commit()
                    logger.debug(f"[Brain] 已記錄預約訊息 (ID: {booking_message.id})")

                    # 轉發到 MCP Server
                    forward_result = await crm_client.forward_line_event(
                        user_id=user_id,
                        message_text=message_text,
                        event_type="message"
                    )

                    if forward_result.get("success"):
                        logger.info("[Booking] 已轉發到 MCP Server")
                    else:
                        logger.warning(f"[Booking] 轉發失敗: {forward_result.get('error')}")
                        await line_client.reply_message(
                            user_id,
                            "抱歉，預約系統暫時無法使用，請稍後再試或直接聯繫客服。"
                        )

                    continue  # 會員預約不進入草稿生成流程
                else:
                    # === 非會員 → 走正常草稿生成，讓 AI 引導付費租借方案 ===
                    logger.info("[Booking] 非會員，走正常草稿生成（引導付費租借）")
                    # 不 continue，繼續往下走草稿生成流程
                    # 把 suggested_intent 標記為會議室租借
                    suggested_intent = "會議室租借"

            # === PHOTO 意圖 → 發送照片 Flex Message ===
            if complexity == "PHOTO":
                logger.info("[Photo] LLM 判斷為看照片意圖")

                # 記錄訊息到 Brain
                photo_message = Message(
                    source="line_oa",
                    sender_id=user_id,
                    sender_name=user_name,
                    content=message_text,
                    status="sent",  # 自動處理，標記為已發送
                    priority="low"
                )
                db.add(photo_message)
                await db.commit()
                logger.debug(f"[Brain] 已記錄照片請求 (ID: {photo_message.id})")

                # 發送照片 Flex Message
                from services.photo_service import send_photos_to_user
                photo_result = await send_photos_to_user(user_id, category="all")

                if photo_result.get("success"):
                    logger.info(f"[Photo] 照片已發送給 {user_name}")
                else:
                    logger.warning(f"[Photo] 照片發送失敗: {photo_result.get('error')}")
                    # 發送失敗時，回覆文字訊息
                    await line_client.reply_message(
                        user_id,
                        "抱歉，照片暫時無法載入，您可以直接來現場參觀，或加 LINE 私訊我們索取照片～"
                    )

                continue  # 照片意圖不進入草稿生成流程

            # === 其他意圖 → 正常草稿生成 ===
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

            # 背景生成草稿（使用獨立 Session，傳入 routing 結果避免重複 API 呼叫）
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

                                logger.info(f"自動模式：已發送草稿給 {user_name}")

                    except Exception as e:
                        logger.error(f"背景草稿生成/發送失敗: {e}")

            background_tasks.add_task(generate_draft_task)

    # LINE 要求回傳 200
    return {"status": "ok"}
