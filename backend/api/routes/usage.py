"""
Brain - API 用量統計路由
追蹤和顯示 AI API 使用情況
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from db.database import get_db
from db.models import APIUsage

router = APIRouter()

# AI API 價格 (每百萬 tokens，美分)
# 包含 Anthropic 直連和 OpenRouter 的模型
PRICING = {
    # === Anthropic 直連模型 ===
    "claude-3-5-sonnet-20241022": {"input": 300, "output": 1500},  # $3/$15 per MTok
    "claude-sonnet-4-5-20250929": {"input": 300, "output": 1500},
    "claude-sonnet-4-5": {"input": 300, "output": 1500},
    "claude-3-5-haiku-20241022": {"input": 100, "output": 500},    # $1/$5 per MTok

    # === OpenRouter 模型 ===
    # Claude 系列 (via OpenRouter)
    "anthropic/claude-sonnet-4.5": {"input": 300, "output": 1500},  # Claude Sonnet 4.5
    "anthropic/claude-3.5-sonnet": {"input": 300, "output": 1500},  # 舊版
    "anthropic/claude-3-haiku": {"input": 25, "output": 125},      # $0.25/$1.25 per MTok

    # Google Gemini 系列 (便宜且快速)
    "google/gemini-flash-1.5": {"input": 7.5, "output": 30},       # $0.075/$0.30 per MTok
    "google/gemini-flash-1.5-8b": {"input": 3.75, "output": 15},   # $0.0375/$0.15 per MTok
    "google/gemini-pro-1.5": {"input": 125, "output": 500},        # $1.25/$5.00 per MTok

    # Meta Llama 系列 (最便宜)
    "meta-llama/llama-3.1-8b-instruct": {"input": 5, "output": 5}, # $0.05/$0.05 per MTok
    "meta-llama/llama-3.1-70b-instruct": {"input": 35, "output": 40},

    # DeepSeek (便宜且強大)
    "deepseek/deepseek-chat": {"input": 14, "output": 28},         # $0.14/$0.28 per MTok

    # 預設價格
    "default": {"input": 300, "output": 1500}
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> int:
    """計算預估費用（美分）"""
    pricing = PRICING.get(model, PRICING["default"])
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return int((input_cost + output_cost) * 100)  # 轉換為分的分（0.01美分）


@router.get("/usage/stats")
async def get_usage_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    取得 API 用量統計

    Args:
        days: 統計天數（預設 30 天）
    """
    since = datetime.utcnow() - timedelta(days=days)

    # 總用量
    total_result = await db.execute(
        select(
            func.sum(APIUsage.input_tokens).label("total_input"),
            func.sum(APIUsage.output_tokens).label("total_output"),
            func.sum(APIUsage.total_tokens).label("total_tokens"),
            func.sum(APIUsage.estimated_cost).label("total_cost"),
            func.count(APIUsage.id).label("total_calls")
        ).where(APIUsage.created_at >= since)
    )
    totals = total_result.first()

    # 今日用量
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(
            func.sum(APIUsage.input_tokens).label("input"),
            func.sum(APIUsage.output_tokens).label("output"),
            func.sum(APIUsage.total_tokens).label("tokens"),
            func.sum(APIUsage.estimated_cost).label("cost"),
            func.count(APIUsage.id).label("calls")
        ).where(APIUsage.created_at >= today_start)
    )
    today = today_result.first()

    # 按日統計（最近7天）
    daily_stats = []
    for i in range(7):
        day_start = (datetime.utcnow() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_result = await db.execute(
            select(
                func.sum(APIUsage.total_tokens).label("tokens"),
                func.sum(APIUsage.estimated_cost).label("cost"),
                func.count(APIUsage.id).label("calls")
            ).where(
                and_(
                    APIUsage.created_at >= day_start,
                    APIUsage.created_at < day_end
                )
            )
        )
        day_data = day_result.first()
        daily_stats.append({
            "date": day_start.strftime("%m/%d"),
            "tokens": day_data.tokens or 0,
            "cost": (day_data.cost or 0) / 100,  # 轉回美分
            "calls": day_data.calls or 0
        })

    daily_stats.reverse()  # 按時間順序排列

    # 按操作類型統計
    by_operation = await db.execute(
        select(
            APIUsage.operation,
            func.sum(APIUsage.total_tokens).label("tokens"),
            func.sum(APIUsage.estimated_cost).label("cost"),
            func.count(APIUsage.id).label("calls")
        ).where(APIUsage.created_at >= since)
        .group_by(APIUsage.operation)
    )
    operations = [
        {
            "operation": row.operation,
            "tokens": row.tokens or 0,
            "cost": (row.cost or 0) / 100,
            "calls": row.calls or 0
        }
        for row in by_operation.fetchall()
    ]

    # 錯誤統計
    error_count = await db.execute(
        select(func.count(APIUsage.id))
        .where(
            and_(
                APIUsage.created_at >= since,
                APIUsage.success == False
            )
        )
    )
    errors = error_count.scalar() or 0

    return {
        "period_days": days,
        "total": {
            "input_tokens": totals.total_input or 0,
            "output_tokens": totals.total_output or 0,
            "total_tokens": totals.total_tokens or 0,
            "estimated_cost_usd": (totals.total_cost or 0) / 10000,  # 轉回美元
            "api_calls": totals.total_calls or 0,
            "errors": errors
        },
        "today": {
            "input_tokens": today.input or 0,
            "output_tokens": today.output or 0,
            "total_tokens": today.tokens or 0,
            "estimated_cost_usd": (today.cost or 0) / 10000,
            "api_calls": today.calls or 0
        },
        "daily": daily_stats,
        "by_operation": operations
    }


@router.get("/usage/recent")
async def get_recent_usage(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """取得最近的 API 調用記錄"""
    result = await db.execute(
        select(APIUsage)
        .order_by(APIUsage.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()

    return {
        "records": [
            {
                "id": r.id,
                "provider": r.provider,
                "model": r.model,
                "operation": r.operation,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost_usd": r.estimated_cost / 10000,
                "success": r.success,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ]
    }


async def log_api_usage(
    db: AsyncSession,
    provider: str,
    model: str,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    success: bool = True,
    error_message: Optional[str] = None
):
    """記錄 API 使用量（供其他模組呼叫）"""
    total_tokens = input_tokens + output_tokens
    estimated_cost = calculate_cost(model, input_tokens, output_tokens)

    usage = APIUsage(
        provider=provider,
        model=model,
        operation=operation,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        success=success,
        error_message=error_message
    )

    db.add(usage)
    await db.commit()

    return usage
