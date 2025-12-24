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
    KnowledgeSuggestion,
    KnowledgeItem,
)
from services.claude_client import get_claude_client
import json
import re


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

    refine_prompt = f"""你是 Hour Jungle 的智能助手，負責三件事：
1. 修正客服回覆草稿
2. 與操作者討論客戶處理策略
3. 識別並提取有價值的知識

## 當前草稿（供參考）
{current_content}

## 操作者輸入
{request.instruction}

## 首先：判斷操作者意圖

**操作者可能是在：**

### A. 給修正指令
例如：「語氣更親切」「加入價格」「更簡潔」
→ 根據指令修正草稿

### B. 表達情緒/決策
例如：「不想理他了」「這客戶一直騙我」「放棄這個」
→ 不要修正草稿，給予理解和建議（如：使用「封存」功能）

### C. 分享對話/討論（重要！）
特徵：
- 輸入內容很長（超過 100 字）
- 包含「您好」「建議」「處理建議」「回覆草案」等詞
- 看起來像是貼上的 AI 對話、處理策略、或專業分析
→ 這是操作者貼上「與其他 AI 的對話」或「處理筆記」
→ 不需要修正草稿
→ **重點是提取其中的知識點！**

### D. 詢問建議
例如：「這個客戶怎麼處理？」「應該怎麼回覆？」
→ 給予策略建議

## 知識提取規則（非常重要！）

### 什麼是可儲存的知識？
1. **處理策略**：如何處理特定類型客戶（逾期、騙子、問題客戶）
2. **回覆模板**：專業的回覆範本（拒絕續約、催繳、通知）
3. **法律/稅務**：國稅局通報、合約終止、押金處理規定
4. **流程步驟**：遷出登記流程、退款流程
5. **客戶背景**：特定客戶的歷史記錄、風險標註
6. **SPIN 應用**：銷售或客戶管理中的 SPIN 實例

### 什麼不是知識？
- 純粹的語氣調整指令
- 格式調整
- 情緒發洩

## 輸出格式

```json
{{
  "operator_intent": "refinement/decision/emotion/discussion/question 擇一",
  "refined_content": "根據意圖：修正後的草稿 / 理解與建議 / 討論回應 / 策略建議",
  "knowledge_detected": true 或 false,
  "knowledge_items": [
    {{
      "content": "知識點1的內容",
      "category": "process/objection/customer_info/faq/service_info/template 擇一",
      "reason": "為什麼值得儲存"
    }},
    {{
      "content": "知識點2的內容",
      "category": "...",
      "reason": "..."
    }}
  ]
}}
```

**knowledge_items 說明：**
- 可以有多個知識點（陣列）
- 如果沒有知識點，設為空陣列 []
- category 新增 "template"（回覆模板）

## 範例

### 範例 1：操作者貼上處理策略
輸入：「這個客戶怎麼處理？不太想理他了 已經通報國稅局無營業事實...（後面是長篇策略分析）」

輸出：
```json
{{
  "operator_intent": "discussion",
  "refined_content": "收到！這個案例處理得很完整。既然已通報國稅局，確實不應再收款。我已識別出 3 個知識點可以儲存，方便日後遇到類似情況時參考。",
  "knowledge_detected": true,
  "knowledge_items": [
    {{
      "content": "【問題客戶退場流程】1. 拒絕收款（已匯則退回）2. 書面告知終止 3. 要求遷出登記證明 4. 憑證明退押金",
      "category": "process",
      "reason": "標準化的問題客戶退場 SOP"
    }},
    {{
      "content": "【拒絕續約回覆模板】許小姐您好，這裡是 Hour Jungle。由於您的合約已於 X 到期，我們在多次提醒後仍未收到正式續約文件與全額款項。基於場域管理規範與法遵要求...",
      "category": "template",
      "reason": "專業的拒絕續約回覆範本"
    }},
    {{
      "content": "【法遵提醒】一旦向國稅局通報「無營業事實」，若再收受該客戶租金並簽署新約，將產生法律與稅務矛盾",
      "category": "service_info",
      "reason": "重要的法律/稅務注意事項"
    }}
  ]
}}
```

### 範例 2：簡單的修正指令
輸入：「語氣更親切一點」
輸出：
```json
{{
  "operator_intent": "refinement",
  "refined_content": "（修正後的草稿，語氣更親切）",
  "knowledge_detected": false,
  "knowledge_items": []
}}
```"""

    try:
        response = await claude_client.generate_response(
            prompt=refine_prompt,
            max_tokens=2500  # 增加輸出長度以容納多個知識點
        )
        raw_content = response.get("content", "")
        model_used = response.get("model", "unknown")
        input_tokens = response.get("usage", {}).get("input_tokens", 0)
        output_tokens = response.get("usage", {}).get("output_tokens", 0)

        # 解析 JSON 回應
        refined_content = current_content
        knowledge_suggestion = KnowledgeSuggestion(detected=False)

        try:
            # 嘗試提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', raw_content)
            if json_match:
                parsed = json.loads(json_match.group(0))
                refined_content = parsed.get("refined_content", current_content)

                # 解析 knowledge_items（新格式：多個知識點）
                knowledge_items_raw = parsed.get("knowledge_items", [])
                if parsed.get("knowledge_detected") and knowledge_items_raw:
                    # 轉換為 KnowledgeItem 物件
                    knowledge_items = []
                    for item in knowledge_items_raw:
                        if isinstance(item, dict) and item.get("content"):
                            knowledge_items.append(KnowledgeItem(
                                content=item.get("content", ""),
                                category=item.get("category", "faq"),
                                reason=item.get("reason", "")
                            ))

                    # 建立 KnowledgeSuggestion（同時填充向後兼容欄位）
                    first_item = knowledge_items[0] if knowledge_items else None
                    knowledge_suggestion = KnowledgeSuggestion(
                        detected=True,
                        items=knowledge_items,
                        # 向後兼容：填充第一個知識點到舊欄位
                        content=first_item.content if first_item else None,
                        category=first_item.category if first_item else None,
                        reason=first_item.reason if first_item else None
                    )
                # 向後兼容：支援舊格式 (knowledge_content/knowledge_category/knowledge_reason)
                elif parsed.get("knowledge_detected") and parsed.get("knowledge_content"):
                    knowledge_suggestion = KnowledgeSuggestion(
                        detected=True,
                        items=[KnowledgeItem(
                            content=parsed.get("knowledge_content", ""),
                            category=parsed.get("knowledge_category", "faq"),
                            reason=parsed.get("knowledge_reason", "")
                        )],
                        content=parsed.get("knowledge_content"),
                        category=parsed.get("knowledge_category"),
                        reason=parsed.get("knowledge_reason")
                    )
            else:
                # 如果沒有 JSON，直接使用原始內容
                refined_content = raw_content.strip()
        except json.JSONDecodeError:
            # JSON 解析失敗，使用原始內容
            refined_content = raw_content.strip()

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

    # 建構回應（包含 knowledge_suggestion）
    return RefinementRead(
        id=refinement.id,
        round_number=refinement.round_number,
        instruction=refinement.instruction,
        original_content=refinement.original_content,
        refined_content=refinement.refined_content,
        model_used=refinement.model_used,
        is_accepted=refinement.is_accepted,
        created_at=refinement.created_at,
        knowledge_suggestion=knowledge_suggestion
    )


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
