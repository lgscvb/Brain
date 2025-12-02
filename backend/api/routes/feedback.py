"""
Brain - 回饋管理 API 路由
支援 AI 自我進化系統的回饋收集
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from db.database import get_db
from db.models import Draft, Response
from db.schemas import DraftFeedback, DraftRead
from pydantic import BaseModel


router = APIRouter()


class FeedbackStats(BaseModel):
    """回饋統計 Schema"""
    total_feedbacks: int
    positive_count: int      # is_good = True
    negative_count: int      # is_good = False
    avg_rating: Optional[float]
    rating_distribution: dict  # {1: 5, 2: 3, 3: 10, 4: 20, 5: 15}
    common_issues: List[str]   # 最常見的改進標籤


class FeedbackListItem(BaseModel):
    """回饋列表項目"""
    draft_id: int
    content: str
    is_good: Optional[bool]
    rating: Optional[int]
    feedback_reason: Optional[str]
    feedback_at: Optional[datetime]
    auto_analysis: Optional[str]
    improvement_tags: Optional[List[str]]

    class Config:
        from_attributes = True


@router.post("/drafts/{draft_id}/feedback")
async def submit_draft_feedback(
    draft_id: int,
    feedback: DraftFeedback,
    db: AsyncSession = Depends(get_db)
):
    """
    提交草稿回饋

    用於 AI 自我進化系統，收集人工對 AI 草稿的評價。

    Args:
        draft_id: 草稿 ID
        feedback: 回饋內容
            - is_good: 快速回饋（好/不好）
            - rating: 評分（1-5 星）
            - feedback_reason: 修改/不好的原因
    """
    # 取得草稿
    result = await db.execute(
        select(Draft).where(Draft.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    # 驗證評分範圍
    if feedback.rating is not None and (feedback.rating < 1 or feedback.rating > 5):
        raise HTTPException(status_code=400, detail="評分必須在 1-5 之間")

    # 更新回饋欄位
    if feedback.is_good is not None:
        draft.is_good = feedback.is_good
    if feedback.rating is not None:
        draft.rating = feedback.rating
    if feedback.feedback_reason is not None:
        draft.feedback_reason = feedback.feedback_reason

    draft.feedback_at = datetime.utcnow()

    # 如果有負面回饋，可以觸發 AI 分析（未來擴展）
    if feedback.is_good is False or (feedback.rating and feedback.rating <= 2):
        # TODO: 觸發 AI 分析改進標籤
        pass

    await db.commit()
    await db.refresh(draft)

    return {
        "success": True,
        "message": "回饋已記錄",
        "draft_id": draft_id,
        "feedback_at": draft.feedback_at
    }


@router.get("/drafts/{draft_id}/feedback")
async def get_draft_feedback(
    draft_id: int,
    db: AsyncSession = Depends(get_db)
):
    """取得單一草稿的回饋資訊"""
    result = await db.execute(
        select(Draft).where(Draft.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    return {
        "draft_id": draft.id,
        "is_good": draft.is_good,
        "rating": draft.rating,
        "feedback_reason": draft.feedback_reason,
        "feedback_at": draft.feedback_at,
        "auto_analysis": draft.auto_analysis,
        "improvement_tags": draft.improvement_tags
    }


@router.get("/feedback/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    取得回饋統計資料

    用於分析 AI 草稿品質和改進方向。
    """
    # 總回饋數
    total_result = await db.execute(
        select(func.count(Draft.id)).where(Draft.feedback_at.isnot(None))
    )
    total_feedbacks = total_result.scalar() or 0

    # 正面/負面回饋數
    positive_result = await db.execute(
        select(func.count(Draft.id)).where(Draft.is_good == True)
    )
    positive_count = positive_result.scalar() or 0

    negative_result = await db.execute(
        select(func.count(Draft.id)).where(Draft.is_good == False)
    )
    negative_count = negative_result.scalar() or 0

    # 平均評分
    avg_result = await db.execute(
        select(func.avg(Draft.rating)).where(Draft.rating.isnot(None))
    )
    avg_rating = avg_result.scalar()

    # 評分分布
    rating_distribution = {}
    for i in range(1, 6):
        count_result = await db.execute(
            select(func.count(Draft.id)).where(Draft.rating == i)
        )
        rating_distribution[i] = count_result.scalar() or 0

    # 常見問題標籤（從 improvement_tags 統計）
    # SQLite JSON 支援有限，這裡先返回空列表，未來可改用更好的統計方式
    common_issues = []

    return FeedbackStats(
        total_feedbacks=total_feedbacks,
        positive_count=positive_count,
        negative_count=negative_count,
        avg_rating=round(avg_rating, 2) if avg_rating else None,
        rating_distribution=rating_distribution,
        common_issues=common_issues
    )


@router.get("/feedback/list")
async def list_feedbacks(
    is_good: Optional[bool] = None,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    列出所有回饋

    可用於訓練資料匯出或人工審核。
    """
    query = select(Draft).where(Draft.feedback_at.isnot(None))

    if is_good is not None:
        query = query.where(Draft.is_good == is_good)

    if min_rating is not None:
        query = query.where(Draft.rating >= min_rating)

    if max_rating is not None:
        query = query.where(Draft.rating <= max_rating)

    query = query.order_by(desc(Draft.feedback_at)).limit(limit).offset(offset)

    result = await db.execute(query)
    drafts = result.scalars().all()

    return {
        "feedbacks": [
            {
                "draft_id": d.id,
                "content": d.content,
                "is_good": d.is_good,
                "rating": d.rating,
                "feedback_reason": d.feedback_reason,
                "feedback_at": d.feedback_at,
                "auto_analysis": d.auto_analysis,
                "improvement_tags": d.improvement_tags
            }
            for d in drafts
        ],
        "total": len(drafts)
    }


@router.get("/feedback/training-data")
async def export_training_data(
    only_rated: bool = True,
    min_rating: int = 4,
    db: AsyncSession = Depends(get_db)
):
    """
    匯出訓練資料

    匯出高品質的回饋資料，用於未來的 AI 微調或 Prompt 優化。

    Args:
        only_rated: 只匯出有評分的資料
        min_rating: 最低評分（用於篩選高品質回覆）
    """
    query = select(Draft, Response).outerjoin(
        Response, Draft.id == Response.draft_id
    )

    if only_rated:
        query = query.where(Draft.rating.isnot(None))
        query = query.where(Draft.rating >= min_rating)

    result = await db.execute(query)
    rows = result.all()

    training_data = []
    for draft, response in rows:
        item = {
            "draft_content": draft.content,
            "draft_strategy": draft.strategy,
            "draft_intent": draft.intent,
            "is_good": draft.is_good,
            "rating": draft.rating,
            "feedback_reason": draft.feedback_reason,
            "improvement_tags": draft.improvement_tags,
        }

        # 如果有最終回覆，包含修改對比
        if response:
            item["final_content"] = response.final_content
            item["was_modified"] = response.is_modified
            item["modification_reason"] = response.modification_reason

        training_data.append(item)

    return {
        "count": len(training_data),
        "data": training_data
    }
