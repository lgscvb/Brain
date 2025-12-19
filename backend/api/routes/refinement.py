"""
Brain - 草稿修正 API 路由
處理多輪對話修正和訓練資料匯出
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from db.database import get_db
from db.models import Draft, DraftRefinement, TrainingExport, Message, Response
from db.schemas import (
    RefinementRequest,
    RefinementRead,
    RefinementHistory,
    TrainingExportRequest,
    TrainingExportResponse,
)
from services.claude_client import get_claude_client


router = APIRouter()


# ==================== 草稿修正 API ====================

@router.post("/drafts/{draft_id}/refine", response_model=RefinementRead)
async def refine_draft(
    draft_id: int,
    request: RefinementRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    提交草稿修正指令，AI 重新生成

    Args:
        draft_id: 草稿 ID
        request: 修正指令（如「語氣更正式一點」）

    Returns:
        修正記錄（含新生成的內容）
    """
    # 取得草稿
    result = await db.execute(
        select(Draft)
        .options(selectinload(Draft.refinements))
        .where(Draft.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    # 計算輪次
    round_number = len(draft.refinements) + 1

    # 取得目前內容（上一輪修正後或原始草稿）
    if draft.refinements:
        # 按輪次排序取最新的
        latest = max(draft.refinements, key=lambda r: r.round_number)
        current_content = latest.refined_content
    else:
        current_content = draft.content

    # 呼叫 AI 修正
    claude_client = get_claude_client()

    refine_prompt = f"""你是一個客服回覆修正助手。

## 原始回覆
{current_content}

## 修正指令
{request.instruction}

## 任務
根據修正指令調整回覆內容。保持專業、有禮貌的語氣。

請直接輸出修正後的回覆，不需要其他說明。"""

    try:
        response = await claude_client.generate_response(
            prompt=refine_prompt,
            max_tokens=1000
        )
        refined_content = response.get("content", current_content)
        model_used = response.get("model", "unknown")
        input_tokens = response.get("usage", {}).get("input_tokens", 0)
        output_tokens = response.get("usage", {}).get("output_tokens", 0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 修正失敗: {str(e)}")

    # 建立修正記錄
    refinement = DraftRefinement(
        draft_id=draft_id,
        round_number=round_number,
        instruction=request.instruction,
        original_content=current_content,
        refined_content=refined_content,
        model_used=model_used,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )

    db.add(refinement)
    await db.commit()
    await db.refresh(refinement)

    return refinement


@router.get("/drafts/{draft_id}/refinements", response_model=RefinementHistory)
async def get_refinement_history(
    draft_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    取得草稿修正歷史

    Args:
        draft_id: 草稿 ID

    Returns:
        修正歷史（含所有修正輪次）
    """
    # 取得草稿
    result = await db.execute(
        select(Draft)
        .options(selectinload(Draft.refinements))
        .where(Draft.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    # 排序修正記錄
    refinements = sorted(draft.refinements, key=lambda r: r.round_number)

    # 取得目前內容
    if refinements:
        current_content = refinements[-1].refined_content
    else:
        current_content = draft.content

    return RefinementHistory(
        draft_id=draft_id,
        original_draft=draft.content,
        current_content=current_content,
        refinements=refinements,
        total_rounds=len(refinements)
    )


@router.post("/drafts/{draft_id}/refinements/{refinement_id}/accept")
async def accept_refinement(
    draft_id: int,
    refinement_id: int,
    db: AsyncSession = Depends(get_db)
):
    """標記修正為已接受"""
    result = await db.execute(
        select(DraftRefinement)
        .where(
            DraftRefinement.id == refinement_id,
            DraftRefinement.draft_id == draft_id
        )
    )
    refinement = result.scalar_one_or_none()

    if not refinement:
        raise HTTPException(status_code=404, detail="修正記錄不存在")

    refinement.is_accepted = True
    await db.commit()

    return {"success": True, "message": "已標記為接受"}


@router.post("/drafts/{draft_id}/refinements/{refinement_id}/reject")
async def reject_refinement(
    draft_id: int,
    refinement_id: int,
    db: AsyncSession = Depends(get_db)
):
    """標記修正為已拒絕"""
    result = await db.execute(
        select(DraftRefinement)
        .where(
            DraftRefinement.id == refinement_id,
            DraftRefinement.draft_id == draft_id
        )
    )
    refinement = result.scalar_one_or_none()

    if not refinement:
        raise HTTPException(status_code=404, detail="修正記錄不存在")

    refinement.is_accepted = False
    await db.commit()

    return {"success": True, "message": "已標記為拒絕"}


# ==================== 訓練資料匯出 API ====================

@router.post("/training/export", response_model=TrainingExportResponse)
async def export_training_data(
    request: TrainingExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    匯出訓練資料

    支援格式：
    - sft: Supervised Fine-Tuning 格式（instruction, input, output）
    - rlhf: RLHF 格式（prompt, chosen, rejected）
    - dpo: Direct Preference Optimization 格式（類似 RLHF）
    """
    data = []

    if request.export_type == "sft":
        data = await _export_sft_data(db, request)
    elif request.export_type == "rlhf":
        data = await _export_rlhf_data(db, request)
    elif request.export_type == "dpo":
        data = await _export_dpo_data(db, request)
    else:
        raise HTTPException(status_code=400, detail=f"不支援的匯出格式: {request.export_type}")

    # 記錄匯出歷史
    export_record = TrainingExport(
        export_type=request.export_type,
        record_count=len(data)
    )
    db.add(export_record)
    await db.commit()
    await db.refresh(export_record)

    return TrainingExportResponse(
        export_type=request.export_type,
        record_count=len(data),
        data=data,
        export_id=export_record.id
    )


async def _export_sft_data(db: AsyncSession, request: TrainingExportRequest) -> list:
    """匯出 SFT 格式資料"""
    data = []

    # 1. 從最終回覆匯出（人工審核過的）
    if request.include_responses:
        result = await db.execute(
            select(Response, Message)
            .join(Message, Response.message_id == Message.id)
            .where(Response.final_content.isnot(None))
        )
        rows = result.all()

        for response, message in rows:
            data.append({
                "instruction": "你是 Hour Jungle 的專業客服助理，請針對客戶訊息提供專業、有禮貌的回覆。",
                "input": message.content,
                "output": response.final_content,
                "metadata": {
                    "source": "response",
                    "message_id": message.id,
                    "is_modified": response.is_modified
                }
            })

    # 2. 從修正對話匯出
    if request.include_refinements:
        result = await db.execute(
            select(DraftRefinement, Draft)
            .join(Draft, DraftRefinement.draft_id == Draft.id)
            .where(DraftRefinement.is_accepted == True)
        )
        rows = result.all()

        for refinement, draft in rows:
            # 修正指令作為 instruction
            data.append({
                "instruction": f"請根據以下指令修正回覆內容：{refinement.instruction}",
                "input": refinement.original_content,
                "output": refinement.refined_content,
                "metadata": {
                    "source": "refinement",
                    "draft_id": draft.id,
                    "round": refinement.round_number
                }
            })

    return data


async def _export_rlhf_data(db: AsyncSession, request: TrainingExportRequest) -> list:
    """匯出 RLHF 格式資料"""
    data = []

    # 從有修改的回覆匯出（原始草稿 vs 修改後）
    result = await db.execute(
        select(Response, Message, Draft)
        .join(Message, Response.message_id == Message.id)
        .outerjoin(Draft, Response.draft_id == Draft.id)
        .where(Response.is_modified == True)
    )
    rows = result.all()

    for response, message, draft in rows:
        if response.original_content and response.final_content:
            data.append({
                "prompt": message.content,
                "chosen": response.final_content,  # 人工修改後的（好的）
                "rejected": response.original_content,  # AI 原始草稿（被拒絕的）
                "metadata": {
                    "message_id": message.id,
                    "modification_reason": response.modification_reason
                }
            })

    # 從修正對話匯出（被拒絕 vs 被接受）
    if request.include_refinements:
        # 取得同一草稿的接受/拒絕對
        result = await db.execute(
            select(Draft)
            .options(selectinload(Draft.refinements))
            .options(selectinload(Draft.message))
        )
        drafts = result.scalars().all()

        for draft in drafts:
            accepted = [r for r in draft.refinements if r.is_accepted == True]
            rejected = [r for r in draft.refinements if r.is_accepted == False]

            # 如果有成對的接受/拒絕
            for a in accepted:
                for r in rejected:
                    if a.instruction == r.instruction:  # 同一個修正指令
                        data.append({
                            "prompt": f"{draft.message.content}\n\n修正指令：{a.instruction}\n原始回覆：{a.original_content}",
                            "chosen": a.refined_content,
                            "rejected": r.refined_content,
                            "metadata": {
                                "draft_id": draft.id,
                                "instruction": a.instruction
                            }
                        })

    return data


async def _export_dpo_data(db: AsyncSession, request: TrainingExportRequest) -> list:
    """匯出 DPO 格式資料（與 RLHF 類似但格式略有不同）"""
    # DPO 格式基本上與 RLHF 相同，但可以加入更多偏好資訊
    rlhf_data = await _export_rlhf_data(db, request)

    # 轉換為 DPO 格式
    dpo_data = []
    for item in rlhf_data:
        dpo_data.append({
            "prompt": item["prompt"],
            "chosen": item["chosen"],
            "rejected": item["rejected"],
            "chosen_rating": 5,  # 假設選中的是 5 分
            "rejected_rating": 2,  # 假設拒絕的是 2 分
            "metadata": item.get("metadata", {})
        })

    return dpo_data


@router.get("/training/stats")
async def get_training_stats(db: AsyncSession = Depends(get_db)):
    """取得訓練資料統計"""

    # 回覆總數
    response_result = await db.execute(select(func.count(Response.id)))
    total_responses = response_result.scalar()

    # 有修改的回覆數
    modified_result = await db.execute(
        select(func.count(Response.id)).where(Response.is_modified == True)
    )
    modified_responses = modified_result.scalar()

    # 修正記錄數
    refinement_result = await db.execute(select(func.count(DraftRefinement.id)))
    total_refinements = refinement_result.scalar()

    # 已接受的修正數
    accepted_result = await db.execute(
        select(func.count(DraftRefinement.id)).where(DraftRefinement.is_accepted == True)
    )
    accepted_refinements = accepted_result.scalar()

    # 匯出歷史
    export_result = await db.execute(
        select(TrainingExport).order_by(TrainingExport.created_at.desc()).limit(10)
    )
    recent_exports = export_result.scalars().all()

    return {
        "total_responses": total_responses,
        "modified_responses": modified_responses,
        "modification_rate": round(modified_responses / total_responses * 100, 1) if total_responses > 0 else 0,
        "total_refinements": total_refinements,
        "accepted_refinements": accepted_refinements,
        "acceptance_rate": round(accepted_refinements / total_refinements * 100, 1) if total_refinements > 0 else 0,
        "estimated_sft_records": total_responses + accepted_refinements,
        "estimated_rlhf_records": modified_responses,
        "recent_exports": [
            {
                "id": e.id,
                "type": e.export_type,
                "count": e.record_count,
                "created_at": e.created_at.isoformat()
            }
            for e in recent_exports
        ]
    }
