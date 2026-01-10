"""
Brain - 訊息分析摘要 API
提供訊息優先級分類、摘要統計、CRM 交叉比對智能建議
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from pydantic import BaseModel
import json

from db.database import get_db
from db.models import Message
from services.jungle_client import get_jungle_client
from services.claude_client import get_claude_client

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


# === 關鍵字定義 ===
URGENT_KEYWORDS = ["急", "緊急", "盡快", "馬上", "立刻", "今天"]
BUSINESS_KEYWORDS = ["續約", "付款", "匯款", "發票", "合約", "簽約", "報價", "費用", "租金", "押金"]
ISSUE_KEYWORDS = ["問題", "故障", "壞了", "不能", "無法", "錯誤", "投訴", "抱怨"]
LOW_PRIORITY_PATTERNS = ["好", "收到", "謝謝", "感謝", "OK", "ok", "了解", "知道了", "👍", "🙏"]


# === Pydantic Models ===
class AnalyzedMessage(BaseModel):
    """已分析的訊息"""
    id: int
    sender_id: str
    sender_name: str
    content: str
    created_at: datetime
    status: str
    priority_level: str  # urgent, business, issue, general, low
    priority_reason: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisSummary(BaseModel):
    """分析摘要"""
    period: str  # 24h, 7d, 30d
    total_messages: int
    pending_count: int

    urgent_count: int
    urgent_messages: List[AnalyzedMessage]

    business_count: int
    business_messages: List[AnalyzedMessage]

    issue_count: int
    issue_messages: List[AnalyzedMessage]

    general_count: int
    low_priority_count: int

    # 建議行動
    action_items: List[str]


class DailySummary(BaseModel):
    """每日摘要"""
    date: str
    message_count: int
    urgent_count: int
    business_count: int
    issue_count: int
    response_rate: float


class AnalysisReport(BaseModel):
    """完整分析報告"""
    generated_at: datetime
    summary: AnalysisSummary
    daily_trends: List[DailySummary]
    top_senders: List[dict]


# === 輔助函數 ===
def classify_message(content: str) -> tuple[str, str]:
    """
    分類訊息優先級
    Returns: (priority_level, reason)
    """
    if not content:
        return "low", "空白訊息"

    content_lower = content.lower()

    # 檢查緊急關鍵字
    for kw in URGENT_KEYWORDS:
        if kw in content:
            return "urgent", f"包含緊急關鍵字「{kw}」"

    # 檢查業務關鍵字
    for kw in BUSINESS_KEYWORDS:
        if kw in content:
            return "business", f"涉及業務事項「{kw}」"

    # 檢查問題關鍵字
    for kw in ISSUE_KEYWORDS:
        if kw in content:
            return "issue", f"可能是問題反映「{kw}」"

    # 檢查低優先級
    stripped = content.strip()
    if len(stripped) <= 5:
        for pattern in LOW_PRIORITY_PATTERNS:
            if pattern in stripped:
                return "low", "簡短回覆"

    return "general", None


# === API 端點 ===
@router.get("/summary", response_model=AnalysisSummary)
async def get_analysis_summary(
    period: str = Query("24h", description="時間範圍: 24h, 7d, 30d"),
    db: AsyncSession = Depends(get_db)
):
    """
    取得訊息分析摘要

    用於 Dashboard 卡片和 Messages 頁面頂部
    """
    # 計算時間範圍
    now = datetime.utcnow()
    if period == "24h":
        start_time = now - timedelta(hours=24)
        period_label = "過去 24 小時"
    elif period == "7d":
        start_time = now - timedelta(days=7)
        period_label = "過去 7 天"
    else:
        start_time = now - timedelta(days=30)
        period_label = "過去 30 天"

    # 查詢訊息
    result = await db.execute(
        select(Message)
        .where(Message.created_at >= start_time)
        .order_by(desc(Message.created_at))
    )
    messages = result.scalars().all()

    # 分類訊息
    urgent_messages = []
    business_messages = []
    issue_messages = []
    general_count = 0
    low_count = 0
    pending_count = 0

    for msg in messages:
        if msg.status in ['pending', 'drafted']:
            pending_count += 1

        level, reason = classify_message(msg.content)
        analyzed = AnalyzedMessage(
            id=msg.id,
            sender_id=msg.sender_id,
            sender_name=msg.sender_name or "未知",
            content=msg.content[:200] if msg.content else "",
            created_at=msg.created_at,
            status=msg.status,
            priority_level=level,
            priority_reason=reason
        )

        if level == "urgent":
            urgent_messages.append(analyzed)
        elif level == "business":
            business_messages.append(analyzed)
        elif level == "issue":
            issue_messages.append(analyzed)
        elif level == "low":
            low_count += 1
        else:
            general_count += 1

    # 生成行動建議
    action_items = []
    if urgent_messages:
        action_items.append(f"🔴 {len(urgent_messages)} 則緊急訊息需要立即處理")
    if business_messages:
        action_items.append(f"💼 {len(business_messages)} 則業務相關訊息待跟進")
    if issue_messages:
        action_items.append(f"⚠️ {len(issue_messages)} 則可能是問題反映，建議優先回覆")
    if pending_count > 10:
        action_items.append(f"📬 累積 {pending_count} 則未處理訊息，建議儘快處理")

    return AnalysisSummary(
        period=period_label,
        total_messages=len(messages),
        pending_count=pending_count,
        urgent_count=len(urgent_messages),
        urgent_messages=urgent_messages[:5],  # 只返回前 5 則
        business_count=len(business_messages),
        business_messages=business_messages[:5],
        issue_count=len(issue_messages),
        issue_messages=issue_messages[:5],
        general_count=general_count,
        low_priority_count=low_count,
        action_items=action_items
    )


@router.get("/report", response_model=AnalysisReport)
async def get_analysis_report(
    db: AsyncSession = Depends(get_db)
):
    """
    取得完整分析報告

    用於獨立的「分析報告」頁面
    """
    now = datetime.utcnow()
    start_time = now - timedelta(days=7)

    # 取得摘要
    summary = await get_analysis_summary("7d", db)

    # 計算每日趨勢
    daily_trends = []
    for i in range(7):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        result = await db.execute(
            select(Message)
            .where(and_(
                Message.created_at >= day_start,
                Message.created_at < day_end
            ))
        )
        day_messages = result.scalars().all()

        urgent = business = issue = 0
        sent = 0
        for msg in day_messages:
            level, _ = classify_message(msg.content)
            if level == "urgent":
                urgent += 1
            elif level == "business":
                business += 1
            elif level == "issue":
                issue += 1
            if msg.status == "sent":
                sent += 1

        daily_trends.append(DailySummary(
            date=day_start.strftime("%m/%d"),
            message_count=len(day_messages),
            urgent_count=urgent,
            business_count=business,
            issue_count=issue,
            response_rate=round(sent / len(day_messages) * 100, 1) if day_messages else 0
        ))

    daily_trends.reverse()  # 最舊的在前

    # 統計活躍發送者
    sender_result = await db.execute(
        select(
            Message.sender_name,
            func.count(Message.id).label('count')
        )
        .where(Message.created_at >= start_time)
        .group_by(Message.sender_name)
        .order_by(desc('count'))
        .limit(10)
    )
    top_senders = [
        {"name": row.sender_name or "未知", "count": row.count}
        for row in sender_result.all()
    ]

    return AnalysisReport(
        generated_at=now,
        summary=summary,
        daily_trends=daily_trends,
        top_senders=top_senders
    )


# === CRM 智能建議 API ===

class ActionSuggestion(BaseModel):
    """建議動作"""
    id: str
    customer_id: Optional[int] = None
    customer_name: str
    line_user_id: str
    message_summary: str
    message_time: datetime
    intent: str  # payment_notice, renewal_confirm, renewal_discuss, termination, inquiry, other
    confidence: float
    suggested_action: str  # record_payment, confirm_renewal, create_draft, follow_up, reply
    action_label: str  # 人類可讀的動作標籤
    action_params: Optional[Dict[str, Any]] = None
    crm_context: Optional[Dict[str, Any]] = None  # 關聯的 CRM 資料

    class Config:
        from_attributes = True


class CRMInsightsResponse(BaseModel):
    """CRM 智能建議回應"""
    generated_at: datetime
    total_messages: int
    analyzed_count: int
    suggestions: List[ActionSuggestion]
    summary: str


# LLM 意圖分析 Prompt
INTENT_ANALYSIS_PROMPT = """你是一個專業的客服訊息分析助手。請分析以下客戶訊息，判斷其意圖。

客戶訊息：
{messages}

請以 JSON 格式回應，包含以下欄位：
{{
  "intent": "意圖類型",
  "confidence": 0.0-1.0 的信心度,
  "summary": "訊息摘要（一句話）",
  "key_info": {{
    "amount": 金額（如有提到）,
    "date": 日期（如有提到）,
    "action": 客戶想做什麼
  }}
}}

意圖類型說明：
- payment_notice: 客戶說已經付款/匯款
- renewal_confirm: 客戶確認要續約
- renewal_discuss: 客戶想討論續約細節（價格、方案等）
- termination: 客戶表示不續約/要退租
- inquiry: 一般詢問
- other: 其他

只回傳 JSON，不要有其他文字。"""


async def analyze_message_intent(messages: List[str]) -> Dict[str, Any]:
    """使用 LLM 分析訊息意圖"""
    claude_client = get_claude_client()

    # 組合訊息
    combined = "\n".join([f"- {m}" for m in messages[-5:]])  # 只取最近 5 則

    try:
        from config import settings
        # 使用 Fast Model 降低成本
        result = await claude_client.generate_response(
            prompt=INTENT_ANALYSIS_PROMPT.format(messages=combined),
            model=settings.MODEL_FAST,
            max_tokens=300,
            temperature=0.3
        )

        # 解析 JSON
        content = result.get("content", "")
        if content:
            try:
                # 嘗試直接解析
                return json.loads(content)
            except json.JSONDecodeError:
                # 嘗試提取 JSON
                import re
                match = re.search(r'\{[\s\S]*\}', content)
                if match:
                    return json.loads(match.group(0))
    except Exception as e:
        print(f"⚠️ LLM 分析失敗: {e}")

    # 回退到關鍵字分析
    text = " ".join(messages).lower()
    if any(kw in text for kw in ["匯款", "付款", "轉帳", "已繳"]):
        return {"intent": "payment_notice", "confidence": 0.7, "summary": "客戶提到付款相關"}
    elif any(kw in text for kw in ["續約", "續租", "繼續租"]):
        if any(kw in text for kw in ["多少", "價格", "討論", "問"]):
            return {"intent": "renewal_discuss", "confidence": 0.6, "summary": "客戶想討論續約"}
        return {"intent": "renewal_confirm", "confidence": 0.6, "summary": "客戶表達續約意願"}
    elif any(kw in text for kw in ["不租", "退租", "不續"]):
        return {"intent": "termination", "confidence": 0.7, "summary": "客戶表示不續約"}

    return {"intent": "other", "confidence": 0.5, "summary": "需要人工判斷"}


def get_action_for_intent(intent: str, crm_data: Dict[str, Any]) -> tuple[str, str, Dict]:
    """根據意圖和 CRM 資料決定建議動作"""
    if intent == "payment_notice":
        # 查找待繳款項
        if crm_data.get("payment_status", {}).get("overdue"):
            return (
                "record_payment",
                "記錄收款",
                {"amount": crm_data["payment_status"].get("overdue_amount")}
            )
        return ("record_payment", "記錄收款", {})

    elif intent == "renewal_confirm":
        contracts = crm_data.get("contracts", [])
        active_contract = next((c for c in contracts if c.get("status") == "active"), None)
        if active_contract:
            return (
                "confirm_renewal",
                "確認續約意願",
                {"contract_id": active_contract.get("id")}
            )
        return ("follow_up", "跟進處理", {})

    elif intent == "renewal_discuss":
        return ("create_draft", "準備續約草稿", {})

    elif intent == "termination":
        contracts = crm_data.get("contracts", [])
        active_contract = next((c for c in contracts if c.get("status") == "active"), None)
        if active_contract:
            return (
                "create_termination",
                "建立解約案件",
                {"contract_id": active_contract.get("id")}
            )
        return ("follow_up", "跟進處理", {})

    else:
        return ("reply", "回覆訊息", {})


@router.get("/crm-insights", response_model=CRMInsightsResponse)
async def get_crm_insights(
    hours: int = Query(24, description="分析多少小時內的訊息"),
    limit: int = Query(20, description="最多返回幾則建議"),
    db: AsyncSession = Depends(get_db)
):
    """
    CRM 智能建議 API

    分析最近的 LINE 訊息，交叉比對 CRM 待辦事項，生成建議動作。
    用於 CRM Dashboard 顯示「AI 建議」卡片。
    """
    now = datetime.utcnow()
    start_time = now - timedelta(hours=hours)
    jungle_client = get_jungle_client()

    # 1. 查詢未處理的訊息（只取客戶發的，排除 bot 回覆）
    result = await db.execute(
        select(Message)
        .where(and_(
            Message.created_at >= start_time,
            Message.status.in_(["pending", "drafted"]),
            Message.source.notin_(["line_bot", "system"])
        ))
        .order_by(desc(Message.created_at))
    )
    messages = result.scalars().all()

    # 2. 按 sender_id 分組
    sender_messages: Dict[str, List[Message]] = {}
    for msg in messages:
        if msg.sender_id not in sender_messages:
            sender_messages[msg.sender_id] = []
        sender_messages[msg.sender_id].append(msg)

    # 3. 分析每個客戶的訊息
    suggestions = []
    analyzed_count = 0

    for sender_id, msgs in list(sender_messages.items())[:limit]:
        try:
            # 取得 CRM 客戶資料
            crm_data = await jungle_client.get_customer_by_line_id(sender_id)

            # 分析訊息意圖
            message_contents = [m.content for m in msgs if m.content]
            if not message_contents:
                continue

            intent_result = await analyze_message_intent(message_contents)
            analyzed_count += 1

            # 決定建議動作
            action, action_label, action_params = get_action_for_intent(
                intent_result.get("intent", "other"),
                crm_data or {}
            )

            # 組合建議
            latest_msg = msgs[0]
            suggestion = ActionSuggestion(
                id=f"{sender_id}-{latest_msg.id}",
                customer_id=crm_data.get("id") if crm_data else None,
                customer_name=crm_data.get("name") if crm_data else latest_msg.sender_name,
                line_user_id=sender_id,
                message_summary=intent_result.get("summary", message_contents[0][:50]),
                message_time=latest_msg.created_at,
                intent=intent_result.get("intent", "other"),
                confidence=intent_result.get("confidence", 0.5),
                suggested_action=action,
                action_label=action_label,
                action_params=action_params,
                crm_context={
                    "has_active_contract": bool(crm_data and any(
                        c.get("status") == "active" for c in crm_data.get("contracts", [])
                    )),
                    "is_overdue": crm_data.get("payment_status", {}).get("overdue", False) if crm_data else False,
                    "company_name": crm_data.get("company_name") if crm_data else None
                }
            )
            suggestions.append(suggestion)

        except Exception as e:
            print(f"⚠️ 分析 {sender_id} 失敗: {e}")
            continue

    # 4. 生成摘要
    intent_counts = {}
    for s in suggestions:
        intent_counts[s.intent] = intent_counts.get(s.intent, 0) + 1

    summary_parts = []
    if intent_counts.get("payment_notice"):
        summary_parts.append(f"{intent_counts['payment_notice']} 位客戶提到付款")
    if intent_counts.get("renewal_confirm") or intent_counts.get("renewal_discuss"):
        count = intent_counts.get("renewal_confirm", 0) + intent_counts.get("renewal_discuss", 0)
        summary_parts.append(f"{count} 位客戶談續約")
    if intent_counts.get("termination"):
        summary_parts.append(f"{intent_counts['termination']} 位客戶表示不續約")

    summary = "、".join(summary_parts) if summary_parts else "目前沒有需要處理的訊息"

    return CRMInsightsResponse(
        generated_at=now,
        total_messages=len(messages),
        analyzed_count=analyzed_count,
        suggestions=suggestions,
        summary=summary
    )
