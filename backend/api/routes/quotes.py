"""
Brain - 報價單相關 API 路由
分析對話內容，識別客戶需求，建議服務項目
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from db.database import get_db
from db.models import Message, Response
from services.claude_client import get_claude_client
from services.crm_client import get_crm_client, CRMError

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Models
# ============================================================================

class ServicePlanSuggestion(BaseModel):
    """服務方案建議"""
    code: str               # 服務代碼
    name: str               # 服務名稱
    unit_price: float       # 單價
    unit: str               # 單位
    deposit: float = 0      # 押金
    quantity: int = 1       # 數量
    amount: float = 0       # 小計
    confidence: float = 0.8 # LLM 信心度
    reason: str = ""        # 建議原因
    revenue_type: str = "own"       # own=自己收款, referral=代辦服務
    billing_cycle: str = "one_time" # one_time=一次性, monthly=月繳


class QuoteAnalysisRequest(BaseModel):
    """報價分析請求"""
    line_user_id: str
    max_messages: int = 20  # 最多分析幾則訊息


class QuoteAnalysisResponse(BaseModel):
    """報價分析回應"""
    success: bool
    customer_name: Optional[str] = None
    customer_needs: Optional[str] = None  # LLM 總結的客戶需求
    suggested_services: List[ServicePlanSuggestion] = []
    total_amount: float = 0
    total_deposit: float = 0
    analysis_summary: Optional[str] = None
    message: Optional[str] = None


class CreateQuoteRequest(BaseModel):
    """建立報價單請求"""
    line_user_id: str
    service_codes: List[str]
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    discount_amount: float = 0
    discount_note: Optional[str] = None
    notes: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================

async def get_service_plans() -> list:
    """從 CRM 取得服務方案列表"""
    try:
        crm = get_crm_client()
        result = await crm.list_service_plans()

        if result.get("success"):
            return result.get("result", {}).get("plans", [])
        else:
            logger.error(f"CRM API error: {result.get('error')}")
            return []
    except CRMError as e:
        logger.error(f"Failed to get service plans: {e}")
        return []


async def analyze_conversation_with_llm(
    messages: List[Message],
    responses: List[Response],
    service_plans: list
) -> dict:
    """使用 LLM 分析對話，識別客戶需求"""
    client = get_claude_client()

    # 組合對話歷史
    conversation_parts = []
    for msg in messages:
        conversation_parts.append(f"客戶：{msg.content}")
        # 找對應的回覆
        for resp in responses:
            if resp.message_id == msg.id:
                conversation_parts.append(f"客服：{resp.final_content}")
                break

    conversation_text = "\n".join(conversation_parts[-20:])  # 最多 20 則

    # 服務清單
    service_list = "\n".join([
        f"- {p['code']}: {p['name']} (${p['unit_price']}/{p['unit']})"
        for p in service_plans
    ])

    prompt = f"""分析以下客戶對話，識別客戶需求並推薦適合的服務。

## 對話內容
{conversation_text}

## 可用服務
{service_list}

## 任務
1. 總結客戶的主要需求
2. 從可用服務中選擇 1-3 個最適合的服務
3. 解釋為什麼推薦這些服務

請用 JSON 格式回覆：
{{
  "customer_needs": "客戶需求總結（1-2句話）",
  "recommendations": [
    {{
      "code": "服務代碼",
      "reason": "推薦原因",
      "confidence": 0.8  // 0.0-1.0 的信心度
    }}
  ],
  "summary": "整體分析總結"
}}

只輸出 JSON，不要其他內容。"""

    try:
        response = await client.generate_response(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.3
        )

        # 解析 JSON
        import json
        import re

        # 嘗試提取 JSON
        content = response.get("content", "")
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
            return result
        else:
            logger.warning(f"LLM response not JSON: {content}")
            return {
                "customer_needs": "無法分析",
                "recommendations": [],
                "summary": "無法從對話中識別明確需求"
            }

    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return {
            "customer_needs": "分析失敗",
            "recommendations": [],
            "summary": f"分析過程發生錯誤: {e}"
        }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/quotes/analyze", response_model=QuoteAnalysisResponse)
async def analyze_conversation_for_quote(
    request: QuoteAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    分析對話內容，識別客戶需求並建議服務項目

    當使用者在 Brain 前端點擊「報價單」按鈕時調用此 API，
    會分析該客戶的對話歷史，使用 LLM 識別需求，
    並從 CRM 服務價格表中推薦適合的服務。

    Args:
        request: 包含 line_user_id 的請求

    Returns:
        建議的服務項目列表，包含價格資訊
    """
    try:
        # 1. 查詢該用戶的訊息歷史
        result = await db.execute(
            select(Message)
            .where(Message.sender_id == request.line_user_id)
            .order_by(desc(Message.created_at))
            .limit(request.max_messages)
        )
        messages = list(result.scalars().all())

        if not messages:
            return QuoteAnalysisResponse(
                success=False,
                message="找不到該用戶的對話記錄"
            )

        # 取得客戶名稱（排除 bot 回覆）
        customer_msg = next(
            (m for m in messages if m.source not in ('line_bot', 'system')),
            None
        )
        customer_name = customer_msg.sender_name if customer_msg else None

        # 2. 查詢對應的回覆記錄
        message_ids = [m.id for m in messages]
        resp_result = await db.execute(
            select(Response)
            .where(Response.message_id.in_(message_ids))
        )
        responses = list(resp_result.scalars().all())

        # 3. 從 CRM 取得服務方案
        service_plans = await get_service_plans()
        if not service_plans:
            return QuoteAnalysisResponse(
                success=False,
                message="無法取得服務價格表"
            )

        # 4. 使用 LLM 分析對話
        analysis = await analyze_conversation_with_llm(
            messages=messages,
            responses=responses,
            service_plans=service_plans
        )

        # 5. 根據 LLM 建議匹配服務方案
        suggested_services = []
        service_map = {p["code"]: p for p in service_plans}

        for rec in analysis.get("recommendations", []):
            code = rec.get("code")
            if code in service_map:
                plan = service_map[code]

                # 計算金額
                unit_price = float(plan.get("unit_price", 0))
                quantity = 1

                # 月租服務預設 12 個月
                if plan.get("unit") == "月" and plan.get("billing_cycle") in ["monthly", "semi_annual", "annual"]:
                    if "2年" in str(plan.get("min_duration", "")):
                        quantity = 24
                    else:
                        quantity = 12

                suggestion = ServicePlanSuggestion(
                    code=code,
                    name=plan.get("name", ""),
                    unit_price=unit_price,
                    unit=plan.get("unit", ""),
                    deposit=float(plan.get("deposit", 0)),
                    quantity=quantity,
                    amount=unit_price * quantity,
                    confidence=rec.get("confidence", 0.8),
                    reason=rec.get("reason", ""),
                    revenue_type=plan.get("revenue_type", "own"),
                    billing_cycle=plan.get("billing_cycle", "one_time")
                )
                suggested_services.append(suggestion)

        # 6. 計算總金額
        total_amount = sum(s.amount for s in suggested_services)
        total_deposit = sum(s.deposit for s in suggested_services)

        return QuoteAnalysisResponse(
            success=True,
            customer_name=customer_name,
            customer_needs=analysis.get("customer_needs"),
            suggested_services=suggested_services,
            total_amount=total_amount,
            total_deposit=total_deposit,
            analysis_summary=analysis.get("summary")
        )

    except Exception as e:
        logger.error(f"analyze_conversation_for_quote error: {e}")
        return QuoteAnalysisResponse(
            success=False,
            message=f"分析失敗: {str(e)}"
        )


@router.post("/quotes/create")
async def create_quote_from_analysis(request: CreateQuoteRequest):
    """
    根據分析結果建立報價單

    當使用者在前端確認服務項目後，調用此 API 在 CRM 建立報價單。

    Args:
        request: 包含 line_user_id, service_codes 等資訊

    Returns:
        新建報價單資訊
    """
    try:
        crm = get_crm_client()
        result = await crm.create_quote_from_service_plans(
            branch_id=1,  # 預設大忠館
            service_codes=request.service_codes,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            line_user_id=request.line_user_id,
            discount_amount=request.discount_amount,
            discount_note=request.discount_note,
            internal_notes=request.notes
        )

        if result.get("success"):
            quote_result = result.get("result", {})
            return {
                "success": True,
                "quote_id": quote_result.get("quote", {}).get("id"),
                "quote_number": quote_result.get("quote", {}).get("quote_number"),
                "message": quote_result.get("message", "報價單建立成功")
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "建立報價單失敗")
            }

    except CRMError as e:
        logger.error(f"create_quote_from_analysis CRM error: {e}")
        raise HTTPException(status_code=502, detail=f"CRM 服務錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"create_quote_from_analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"建立報價單失敗: {str(e)}")
