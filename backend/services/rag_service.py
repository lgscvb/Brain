"""
Brain - RAG 服務
負責知識檢索和上下文組合
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from db.models import KnowledgeChunk
from services.embedding_client import get_embedding_client
import json


class RAGService:
    """RAG 服務 - 知識檢索增強生成"""

    def __init__(self):
        """初始化 RAG 服務"""
        self.embedding_client = get_embedding_client()

    async def search_knowledge(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        service_type: Optional[str] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        搜尋相關知識

        Args:
            db: 資料庫連線
            query: 搜尋查詢
            top_k: 返回的最大結果數
            category: 篩選分類（可選）
            service_type: 篩選服務類型（可選）
            similarity_threshold: 相似度閾值

        Returns:
            相關知識列表，包含 content, category, similarity 等
        """
        # 生成查詢向量
        query_embedding = await self.embedding_client.embed_text(query)

        if query_embedding is None:
            print("⚠️ 無法生成查詢向量，使用關鍵字搜尋")
            return await self._keyword_search(db, query, top_k, category, service_type)

        # 嘗試使用 pgvector 搜尋
        try:
            return await self._vector_search(
                db, query_embedding, top_k, category, service_type, similarity_threshold
            )
        except Exception as e:
            print(f"⚠️ 向量搜尋失敗: {e}，使用 JSON 備用方案")
            return await self._json_vector_search(
                db, query_embedding, top_k, category, service_type, similarity_threshold
            )

    async def _vector_search(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        top_k: int,
        category: Optional[str],
        service_type: Optional[str],
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """使用 pgvector 進行向量搜尋"""
        # 構建查詢
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        sql = """
            SELECT
                id,
                content,
                category,
                sub_category,
                service_type,
                extra_data,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM knowledge_chunks
            WHERE is_active = TRUE
            AND embedding IS NOT NULL
        """

        params = {"embedding": embedding_str}

        if category:
            sql += " AND category = :category"
            params["category"] = category

        if service_type:
            sql += " AND service_type = :service_type"
            params["service_type"] = service_type

        sql += """
            AND 1 - (embedding <=> :embedding::vector) >= :threshold
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """
        params["threshold"] = similarity_threshold
        params["top_k"] = top_k

        result = await db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "content": row.content,
                "category": row.category,
                "sub_category": row.sub_category,
                "service_type": row.service_type,
                "metadata": row.extra_data,
                "similarity": float(row.similarity)
            }
            for row in rows
        ]

    async def _json_vector_search(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        top_k: int,
        category: Optional[str],
        service_type: Optional[str],
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """使用 JSON 存儲的向量進行搜尋（備用方案）"""
        # 構建基本查詢
        stmt = select(KnowledgeChunk).where(
            KnowledgeChunk.is_active == True,
            KnowledgeChunk.embedding_json.isnot(None)
        )

        if category:
            stmt = stmt.where(KnowledgeChunk.category == category)

        if service_type:
            stmt = stmt.where(KnowledgeChunk.service_type == service_type)

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        # 計算相似度
        results = []
        for chunk in chunks:
            embedding = chunk.embedding_json
            if embedding:
                similarity = self._cosine_similarity(query_embedding, embedding)
                if similarity >= similarity_threshold:
                    results.append({
                        "id": chunk.id,
                        "content": chunk.content,
                        "category": chunk.category,
                        "sub_category": chunk.sub_category,
                        "service_type": chunk.service_type,
                        "metadata": chunk.extra_data,
                        "similarity": similarity
                    })

        # 按相似度排序並取 top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    async def _keyword_search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int,
        category: Optional[str],
        service_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """關鍵字搜尋（Embedding 不可用時的備用方案）"""
        stmt = select(KnowledgeChunk).where(
            KnowledgeChunk.is_active == True,
            KnowledgeChunk.content.ilike(f"%{query}%")
        )

        if category:
            stmt = stmt.where(KnowledgeChunk.category == category)

        if service_type:
            stmt = stmt.where(KnowledgeChunk.service_type == service_type)

        stmt = stmt.limit(top_k)

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        return [
            {
                "id": chunk.id,
                "content": chunk.content,
                "category": chunk.category,
                "sub_category": chunk.sub_category,
                "service_type": chunk.service_type,
                "metadata": chunk.extra_data,
                "similarity": 0.5  # 關鍵字匹配給一個固定分數
            }
            for chunk in chunks
        ]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """計算餘弦相似度"""
        import math
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    async def get_relevant_context(
        self,
        db: AsyncSession,
        message: str,
        top_k: int = 5
    ) -> str:
        """
        獲取與訊息相關的上下文

        Args:
            db: 資料庫連線
            message: 客戶訊息
            top_k: 返回的最大結果數

        Returns:
            格式化的知識上下文字串
        """
        # 搜尋相關知識
        results = await self.search_knowledge(db, message, top_k=top_k)

        if not results:
            return ""

        # 按類別分組
        categories = {}
        for item in results:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        # 格式化輸出
        context_parts = ["## 相關知識\n"]

        category_names = {
            "spin_question": "SPIN 問題庫",
            "value_prop": "價值主張",
            "objection": "異議處理",
            "faq": "常見問題",
            "service_info": "服務資訊"
        }

        for cat, items in categories.items():
            cat_name = category_names.get(cat, cat)
            context_parts.append(f"### {cat_name}")
            for item in items:
                context_parts.append(f"- {item['content']}")
            context_parts.append("")

        return "\n".join(context_parts)

    async def add_knowledge(
        self,
        db: AsyncSession,
        content: str,
        category: str,
        sub_category: Optional[str] = None,
        service_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> KnowledgeChunk:
        """
        添加知識條目

        Args:
            db: 資料庫連線
            content: 知識內容
            category: 分類
            sub_category: 子分類
            service_type: 服務類型
            metadata: 元資料

        Returns:
            新建的 KnowledgeChunk
        """
        # 生成 Embedding
        embedding = await self.embedding_client.embed_text(content)

        chunk = KnowledgeChunk(
            content=content,
            category=category,
            sub_category=sub_category,
            service_type=service_type,
            extra_data=metadata or {},
            embedding_json=embedding  # 存入 JSON 欄位
        )

        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)

        # 如果 pgvector 可用，同時更新 embedding 欄位
        if embedding:
            try:
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"
                await db.execute(
                    text("UPDATE knowledge_chunks SET embedding = :embedding::vector WHERE id = :id"),
                    {"embedding": embedding_str, "id": chunk.id}
                )
                await db.commit()
            except Exception as e:
                print(f"⚠️ pgvector 欄位更新失敗: {e}")

        return chunk


# 全域 RAG 服務實例
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """取得 RAG 服務單例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
