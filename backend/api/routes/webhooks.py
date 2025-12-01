"""
Brain - Webhook API 路由
處理 LINE Webhook 事件
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import Message
from brain.draft_generator import get_draft_generator
from services.line_client import get_line_client


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
        if event.get('type') == 'message' and event.get('message', {}).get('type') == 'text':
            # 取得訊息資訊
            user_id = event.get('source', {}).get('userId', '')
            message_text = event.get('message', {}).get('text', '')
            
            if not user_id or not message_text:
                continue
            
            # 取得用戶資料
            user_profile = await line_client.get_user_profile(user_id)
            sender_name = user_profile.get('display_name', '未知用戶') if user_profile else '未知用戶'
            
            # 建立訊息記錄
            message = Message(
                source="line_oa",
                sender_id=user_id,
                sender_name=sender_name,
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
                async with AsyncSessionLocal() as task_db:
                    draft_generator = get_draft_generator()
                    try:
                        await draft_generator.generate(
                            db=task_db,
                            message_id=message.id,
                            content=message.content,
                            sender_name=message.sender_name,
                            source=message.source
                        )
                    except Exception as e:
                        print(f"背景草稿生成失敗: {str(e)}")
            
            background_tasks.add_task(generate_draft_task)
    
    # LINE 要求回傳 200
    return {"status": "ok"}
