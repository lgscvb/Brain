"""
Brain - 知識庫管理 API
提供知識條目的 CRUD 操作
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.database import get_db
from db.models import KnowledgeChunk
from services.rag_service import get_rag_service

router = APIRouter(prefix="/knowledge", tags=["知識庫管理"])


# === Pydantic Models ===

class KnowledgeCreate(BaseModel):
    """建立知識條目"""
    content: str
    category: str
    sub_category: Optional[str] = None
    service_type: Optional[str] = None
    metadata: Optional[dict] = None


class KnowledgeUpdate(BaseModel):
    """更新知識條目"""
    content: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    service_type: Optional[str] = None
    metadata: Optional[dict] = None
    is_active: Optional[bool] = None


class KnowledgeResponse(BaseModel):
    """知識條目回應"""
    id: int
    content: str
    category: str
    sub_category: Optional[str]
    service_type: Optional[str]
    metadata: Optional[dict]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class KnowledgeListResponse(BaseModel):
    """知識列表回應"""
    items: List[KnowledgeResponse]
    total: int
    page: int
    page_size: int


class SearchRequest(BaseModel):
    """搜尋請求"""
    query: str
    top_k: int = 5
    category: Optional[str] = None
    service_type: Optional[str] = None


class SearchResult(BaseModel):
    """搜尋結果"""
    id: int
    content: str
    category: str
    sub_category: Optional[str]
    service_type: Optional[str]
    similarity: float


# === API Endpoints ===

@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    service_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """取得知識列表"""
    # 建立查詢
    stmt = select(KnowledgeChunk)

    if category:
        stmt = stmt.where(KnowledgeChunk.category == category)
    if service_type:
        stmt = stmt.where(KnowledgeChunk.service_type == service_type)
    if is_active is not None:
        stmt = stmt.where(KnowledgeChunk.is_active == is_active)
    if search:
        stmt = stmt.where(KnowledgeChunk.content.ilike(f"%{search}%"))

    # 計算總數
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # 分頁
    stmt = stmt.order_by(KnowledgeChunk.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    items = result.scalars().all()

    return KnowledgeListResponse(
        items=[
            KnowledgeResponse(
                id=item.id,
                content=item.content,
                category=item.category,
                sub_category=item.sub_category,
                service_type=item.service_type,
                metadata=item.extra_data,
                is_active=item.is_active,
                created_at=item.created_at.isoformat() if item.created_at else "",
                updated_at=item.updated_at.isoformat() if item.updated_at else ""
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """取得所有分類"""
    result = await db.execute(
        select(KnowledgeChunk.category)
        .distinct()
        .where(KnowledgeChunk.is_active == True)
    )
    categories = [row[0] for row in result.fetchall()]

    # 分類名稱對應
    category_names = {
        "spin_question": "SPIN 問題庫",
        "value_prop": "價值主張",
        "objection": "異議處理",
        "faq": "常見問題",
        "service_info": "服務資訊",
        "tactics": "銷售技巧",
        "scenario": "情境範例",
        "example_response": "對話範例"
    }

    return {
        "categories": [
            {"id": cat, "name": category_names.get(cat, cat)}
            for cat in categories
        ]
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """取得知識庫統計"""
    # 總數
    total_result = await db.execute(
        select(func.count()).select_from(KnowledgeChunk)
    )
    total = total_result.scalar()

    # 啟用數
    active_result = await db.execute(
        select(func.count())
        .select_from(KnowledgeChunk)
        .where(KnowledgeChunk.is_active == True)
    )
    active = active_result.scalar()

    # 各分類數量
    category_result = await db.execute(
        select(
            KnowledgeChunk.category,
            func.count(KnowledgeChunk.id)
        )
        .group_by(KnowledgeChunk.category)
    )
    by_category = {row[0]: row[1] for row in category_result.fetchall()}

    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "by_category": by_category
    }


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    """取得單個知識條目"""
    result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.id == knowledge_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    return KnowledgeResponse(
        id=item.id,
        content=item.content,
        category=item.category,
        sub_category=item.sub_category,
        service_type=item.service_type,
        metadata=item.extra_data,
        is_active=item.is_active,
        created_at=item.created_at.isoformat() if item.created_at else "",
        updated_at=item.updated_at.isoformat() if item.updated_at else ""
    )


@router.post("", response_model=KnowledgeResponse)
async def create_knowledge(
    data: KnowledgeCreate,
    db: AsyncSession = Depends(get_db)
):
    """建立知識條目"""
    rag_service = get_rag_service()

    chunk = await rag_service.add_knowledge(
        db=db,
        content=data.content,
        category=data.category,
        sub_category=data.sub_category,
        service_type=data.service_type,
        metadata=data.metadata
    )

    return KnowledgeResponse(
        id=chunk.id,
        content=chunk.content,
        category=chunk.category,
        sub_category=chunk.sub_category,
        service_type=chunk.service_type,
        metadata=chunk.extra_data,
        is_active=chunk.is_active,
        created_at=chunk.created_at.isoformat() if chunk.created_at else "",
        updated_at=chunk.updated_at.isoformat() if chunk.updated_at else ""
    )


@router.put("/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge(
    knowledge_id: int,
    data: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新知識條目"""
    result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.id == knowledge_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    # 更新欄位
    if data.content is not None:
        item.content = data.content
        # 重新生成 Embedding
        rag_service = get_rag_service()
        embedding = await rag_service.embedding_client.embed_text(data.content)
        item.embedding_json = embedding

    if data.category is not None:
        item.category = data.category
    if data.sub_category is not None:
        item.sub_category = data.sub_category
    if data.service_type is not None:
        item.service_type = data.service_type
    if data.metadata is not None:
        item.extra_data = data.metadata
    if data.is_active is not None:
        item.is_active = data.is_active

    await db.commit()
    await db.refresh(item)

    return KnowledgeResponse(
        id=item.id,
        content=item.content,
        category=item.category,
        sub_category=item.sub_category,
        service_type=item.service_type,
        metadata=item.extra_data,
        is_active=item.is_active,
        created_at=item.created_at.isoformat() if item.created_at else "",
        updated_at=item.updated_at.isoformat() if item.updated_at else ""
    )


@router.delete("/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: int,
    db: AsyncSession = Depends(get_db)
):
    """刪除知識條目"""
    result = await db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.id == knowledge_id)
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    await db.delete(item)
    await db.commit()

    return {"status": "success", "message": "Knowledge deleted"}


@router.post("/search", response_model=List[SearchResult])
async def search_knowledge(
    data: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """搜尋知識（向量搜尋）"""
    rag_service = get_rag_service()

    results = await rag_service.search_knowledge(
        db=db,
        query=data.query,
        top_k=data.top_k,
        category=data.category,
        service_type=data.service_type
    )

    return [
        SearchResult(
            id=item["id"],
            content=item["content"],
            category=item["category"],
            sub_category=item.get("sub_category"),
            service_type=item.get("service_type"),
            similarity=item["similarity"]
        )
        for item in results
    ]


@router.post("/bulk-import")
async def bulk_import(
    items: List[KnowledgeCreate],
    db: AsyncSession = Depends(get_db)
):
    """批次匯入知識"""
    rag_service = get_rag_service()
    imported = 0
    errors = []

    for i, item in enumerate(items):
        try:
            await rag_service.add_knowledge(
                db=db,
                content=item.content,
                category=item.category,
                sub_category=item.sub_category,
                service_type=item.service_type,
                metadata=item.metadata
            )
            imported += 1
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    return {
        "status": "success",
        "imported": imported,
        "errors": errors
    }
