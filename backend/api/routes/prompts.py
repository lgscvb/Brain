"""
Brain - Prompt 版本管理 API

【功能】
1. 列出所有 Prompt 及其活躍版本
2. 查看特定 Prompt 的版本歷史
3. 建立新版本
4. 啟用/回滾版本
5. 比較不同版本

【安全考量】
這些 API 會影響 AI 行為，建議加上 Admin 認證
目前暫時開放，生產環境需要加上認證中間件

【使用方式】
```bash
# 列出所有 Prompt
curl http://localhost:8787/api/prompts

# 查看特定 Prompt 的版本歷史
curl http://localhost:8787/api/prompts/draft_prompt

# 建立新版本
curl -X POST http://localhost:8787/api/prompts/draft_prompt \
  -H "Content-Type: application/json" \
  -d '{"content": "新的 Prompt 內容...", "description": "v2: 改進了報價流程"}'

# 啟用特定版本
curl -X PUT http://localhost:8787/api/prompts/draft_prompt/activate/2
```
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from services.prompt_service import get_prompt_service, PromptVersionInfo, PromptSummary

router = APIRouter(prefix="/prompts", tags=["Prompt 版本管理"])


# ============================================================
# Pydantic Models
# ============================================================

class PromptVersionCreate(BaseModel):
    """建立 Prompt 版本請求"""
    content: str = Field(..., description="Prompt 內容")
    description: Optional[str] = Field(None, description="版本說明")
    created_by: str = Field(default="admin", description="建立者")


class PromptVersionResponse(BaseModel):
    """Prompt 版本回應"""
    id: int
    prompt_key: str
    version: int
    content: str
    description: Optional[str]
    is_active: bool
    created_by: str
    created_at: str

    class Config:
        from_attributes = True


class PromptSummaryResponse(BaseModel):
    """Prompt 摘要回應"""
    prompt_key: str
    active_version: Optional[int]
    total_versions: int
    last_updated: Optional[str]


class PromptDetailResponse(BaseModel):
    """Prompt 詳細資訊（含版本歷史）"""
    prompt_key: str
    active_version: Optional[PromptVersionResponse]
    versions: List[PromptVersionResponse]


class ActivateResponse(BaseModel):
    """啟用版本回應"""
    success: bool
    message: str
    prompt_key: str
    activated_version: int


class PromptCompareResponse(BaseModel):
    """版本比較回應"""
    prompt_key: str
    version_a: PromptVersionResponse
    version_b: PromptVersionResponse


# ============================================================
# API Endpoints
# ============================================================

@router.get("", response_model=List[PromptSummaryResponse])
async def list_prompts(
    db: AsyncSession = Depends(get_db)
):
    """
    列出所有 Prompt 及其摘要

    【用途】
    Admin 面板總覽頁面，顯示所有 Prompt 的狀態
    """
    service = get_prompt_service()
    summaries = await service.list_prompts(db)

    return [
        PromptSummaryResponse(
            prompt_key=s["prompt_key"],
            active_version=s["active_version"],
            total_versions=s["total_versions"],
            last_updated=s["last_updated"]
        )
        for s in summaries
    ]


@router.get("/{prompt_key}", response_model=PromptDetailResponse)
async def get_prompt_detail(
    prompt_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    取得特定 Prompt 的詳細資訊

    【包含】
    - 當前活躍版本
    - 所有版本歷史（降序排列）
    """
    service = get_prompt_service()
    versions = await service.get_version_history(db, prompt_key)

    if not versions:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{prompt_key}' not found"
        )

    # 找出活躍版本
    active_version = next(
        (v for v in versions if v["is_active"]),
        None
    )

    return PromptDetailResponse(
        prompt_key=prompt_key,
        active_version=PromptVersionResponse(**active_version) if active_version else None,
        versions=[PromptVersionResponse(**v) for v in versions]
    )


@router.get("/{prompt_key}/version/{version}", response_model=PromptVersionResponse)
async def get_prompt_version(
    prompt_key: str,
    version: int,
    db: AsyncSession = Depends(get_db)
):
    """
    取得特定版本的 Prompt

    【用途】
    查看歷史版本的完整內容
    """
    service = get_prompt_service()
    v = await service.get_version(db, prompt_key, version)

    if not v:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{prompt_key}' version {version} not found"
        )

    return PromptVersionResponse(**v)


@router.post("/{prompt_key}", response_model=PromptVersionResponse)
async def create_prompt_version(
    prompt_key: str,
    data: PromptVersionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    建立新版本

    【說明】
    - 新版本會自動取得下一個版本號
    - 新版本預設不啟用，需要手動啟用

    【範例】
    ```json
    {
        "content": "你是 Hour Jungle 的客服助理...",
        "description": "v2: 改進了報價流程"
    }
    ```
    """
    service = get_prompt_service()

    version_info = await service.create_version(
        db=db,
        prompt_key=prompt_key,
        content=data.content,
        description=data.description,
        created_by=data.created_by
    )

    return PromptVersionResponse(**version_info)


@router.put("/{prompt_key}/activate/{version}", response_model=ActivateResponse)
async def activate_prompt_version(
    prompt_key: str,
    version: int,
    db: AsyncSession = Depends(get_db)
):
    """
    啟用指定版本

    【說明】
    - 會自動停用該 key 的其他所有版本
    - 啟用後立即生效，下一次 AI 呼叫會使用新版本

    【警告】
    啟用新版本可能影響 AI 回覆品質，建議先在測試環境驗證
    """
    service = get_prompt_service()
    success = await service.activate_version(db, prompt_key, version)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{prompt_key}' version {version} not found"
        )

    return ActivateResponse(
        success=True,
        message=f"已啟用 {prompt_key} v{version}",
        prompt_key=prompt_key,
        activated_version=version
    )


@router.put("/{prompt_key}/rollback/{version}", response_model=ActivateResponse)
async def rollback_prompt_version(
    prompt_key: str,
    version: int,
    db: AsyncSession = Depends(get_db)
):
    """
    回滾到指定版本

    【說明】
    功能上等同於 activate，但語義更清晰
    用於「新版本有問題，要切回舊版」的場景

    【範例】
    發現 v3 有 bug，回滾到 v2：
    PUT /api/prompts/draft_prompt/rollback/2
    """
    service = get_prompt_service()
    success = await service.rollback(db, prompt_key, version)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{prompt_key}' version {version} not found"
        )

    return ActivateResponse(
        success=True,
        message=f"已回滾 {prompt_key} 到 v{version}",
        prompt_key=prompt_key,
        activated_version=version
    )


@router.get("/{prompt_key}/compare", response_model=PromptCompareResponse)
async def compare_prompt_versions(
    prompt_key: str,
    version_a: int = Query(..., description="版本 A"),
    version_b: int = Query(..., description="版本 B"),
    db: AsyncSession = Depends(get_db)
):
    """
    比較兩個版本

    【用途】
    在啟用新版本前，比較新舊版本的差異

    【範例】
    GET /api/prompts/draft_prompt/compare?version_a=1&version_b=2
    """
    service = get_prompt_service()

    v_a = await service.get_version(db, prompt_key, version_a)
    v_b = await service.get_version(db, prompt_key, version_b)

    if not v_a:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_a} not found"
        )

    if not v_b:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version_b} not found"
        )

    return PromptCompareResponse(
        prompt_key=prompt_key,
        version_a=PromptVersionResponse(**v_a),
        version_b=PromptVersionResponse(**v_b)
    )


@router.delete("/{prompt_key}/version/{version}")
async def delete_prompt_version(
    prompt_key: str,
    version: int,
    db: AsyncSession = Depends(get_db)
):
    """
    刪除指定版本

    【限制】
    - 不能刪除活躍版本（需要先切換到其他版本）
    - 不能刪除 v1（初始版本保留）

    【用途】
    清理不再需要的舊版本
    """
    service = get_prompt_service()

    try:
        success = await service.delete_version(db, prompt_key, version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{prompt_key}' version {version} not found"
        )

    return {
        "success": True,
        "message": f"已刪除 {prompt_key} v{version}"
    }


@router.get("/{prompt_key}/active-content")
async def get_active_prompt_content(
    prompt_key: str,
    db: AsyncSession = Depends(get_db)
):
    """
    取得活躍版本的 Prompt 內容

    【用途】
    快速取得當前使用的 Prompt 內容
    如果無活躍版本，會回傳預設值

    【回傳】
    純文字 Prompt 內容
    """
    service = get_prompt_service()
    content = await service.get_active_prompt(db, prompt_key)

    return {
        "prompt_key": prompt_key,
        "content": content,
        "is_default": not bool(await service.get_version_history(db, prompt_key))
    }
