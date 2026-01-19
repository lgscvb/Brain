"""
Brain - RAG Service 測試
測試知識檢索和向量搜尋功能
"""
import pytest
import math
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from services.rag_service import RAGService, get_rag_service
from db.models import KnowledgeChunk


# ============================================================
# 純函數測試：_cosine_similarity
# 這是數學計算，不需要任何 mock 或 DB
# ============================================================

class TestCosineSimilarity:
    """測試餘弦相似度計算"""

    def setup_method(self):
        """每個測試前建立 RAGService 實例"""
        self.service = RAGService()

    def test_identical_vectors_return_one(self):
        """
        相同向量應該返回 1.0

        【概念解釋】
        餘弦相似度測量兩個向量的「方向」相似程度：
        - 完全相同方向 = 1.0（夾角 0 度）
        - 垂直 = 0.0（夾角 90 度）
        - 完全相反 = -1.0（夾角 180 度）
        """
        vec = [1.0, 2.0, 3.0]
        result = self.service._cosine_similarity(vec, vec)
        assert abs(result - 1.0) < 1e-9, f"相同向量應該返回 1.0，但得到 {result}"

    def test_orthogonal_vectors_return_zero(self):
        """
        正交（垂直）向量應該返回 0.0

        【範例】
        vec1 = [1, 0] 指向右邊
        vec2 = [0, 1] 指向上方
        它們夾角 90 度，cos(90°) = 0
        """
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        result = self.service._cosine_similarity(vec1, vec2)
        assert abs(result) < 1e-9, f"正交向量應該返回 0.0，但得到 {result}"

    def test_opposite_vectors_return_negative_one(self):
        """
        相反方向向量應該返回 -1.0

        【範例】
        vec1 = [1, 1] 指向右上
        vec2 = [-1, -1] 指向左下（完全相反）
        """
        vec1 = [1.0, 1.0]
        vec2 = [-1.0, -1.0]
        result = self.service._cosine_similarity(vec1, vec2)
        assert abs(result - (-1.0)) < 1e-9, f"相反向量應該返回 -1.0，但得到 {result}"

    def test_zero_vector_returns_zero(self):
        """
        零向量應該返回 0.0（避免除以零錯誤）

        【為什麼重要】
        數學上，零向量沒有方向，所以無法計算相似度。
        我們選擇返回 0.0 表示「無法比較」，而不是拋出錯誤。
        """
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [0.0, 0.0, 0.0]
        result = self.service._cosine_similarity(vec1, vec2)
        assert result == 0.0, f"零向量應該返回 0.0，但得到 {result}"

        # 兩個都是零向量
        result2 = self.service._cosine_similarity(vec2, vec2)
        assert result2 == 0.0

    def test_different_magnitude_same_direction(self):
        """
        相同方向但長度不同的向量應該返回 1.0

        【概念解釋】
        餘弦相似度只看「方向」，不看「長度」：
        - [1, 2, 3] 和 [2, 4, 6] 方向相同，只是長度不同
        - 所以相似度 = 1.0

        這在 NLP 中很重要，因為我們關心的是語意方向，不是向量大小
        """
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [2.0, 4.0, 6.0]  # vec1 的 2 倍
        result = self.service._cosine_similarity(vec1, vec2)
        assert abs(result - 1.0) < 1e-9, f"同方向不同長度應該返回 1.0，但得到 {result}"

    def test_high_dimensional_vectors(self):
        """
        測試高維向量（OpenAI embedding 是 1536 維）

        【實際應用】
        OpenAI 的 text-embedding-3-small 輸出 1536 維向量
        我們需要確保函數能處理這種規模的計算
        """
        # 模擬 1536 維向量
        import random
        random.seed(42)  # 固定種子確保可重複

        vec1 = [random.random() for _ in range(1536)]
        vec2 = [random.random() for _ in range(1536)]

        result = self.service._cosine_similarity(vec1, vec2)

        # 結果應該在 -1 到 1 之間
        assert -1.0 <= result <= 1.0, f"相似度應該在 [-1, 1]，但得到 {result}"

    def test_known_similarity_value(self):
        """
        測試已知結果的向量

        【計算過程】
        vec1 = [3, 4]，長度 = sqrt(9 + 16) = 5
        vec2 = [4, 3]，長度 = sqrt(16 + 9) = 5
        點積 = 3*4 + 4*3 = 24
        相似度 = 24 / (5 * 5) = 0.96
        """
        vec1 = [3.0, 4.0]
        vec2 = [4.0, 3.0]
        result = self.service._cosine_similarity(vec1, vec2)
        expected = 24.0 / 25.0  # = 0.96
        assert abs(result - expected) < 1e-9, f"期望 {expected}，但得到 {result}"


# ============================================================
# 資料庫相關測試：需要 DB session 和測試資料
# ============================================================

class TestKeywordSearch:
    """測試關鍵字搜尋（Embedding 不可用時的備用方案）"""

    @pytest.mark.asyncio
    async def test_finds_matching_content(self, async_client):
        """
        測試關鍵字匹配

        【情境】
        當 Embedding API 不可用時，系統會退回使用 ILIKE 關鍵字搜尋
        """
        from tests.conftest import TestSessionLocal
        from db.models import KnowledgeChunk

        async with TestSessionLocal() as db:
            # 準備測試資料
            chunk = KnowledgeChunk(
                content="虛擬登記地址服務每月只要 800 元",
                category="service_info",
                sub_category="price",
                service_type="address_service",
                is_active=True
            )
            db.add(chunk)
            await db.commit()

            # 執行搜尋
            service = RAGService()
            results = await service._keyword_search(
                db=db,
                query="虛擬登記",
                top_k=5,
                category=None,
                service_type=None
            )

            # 驗證
            assert len(results) == 1
            assert "虛擬登記" in results[0]["content"]
            assert results[0]["similarity"] == 0.5  # 關鍵字搜尋固定給 0.5

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_match(self, async_client):
        """測試無匹配時返回空列表"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            # 準備測試資料（不含搜尋關鍵字）
            chunk = KnowledgeChunk(
                content="會議室租借服務",
                category="service_info",
                is_active=True
            )
            db.add(chunk)
            await db.commit()

            service = RAGService()
            results = await service._keyword_search(
                db=db,
                query="完全不相關的關鍵字",
                top_k=5,
                category=None,
                service_type=None
            )

            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_respects_category_filter(self, async_client):
        """測試分類篩選"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            # 準備不同分類的測試資料
            chunk1 = KnowledgeChunk(
                content="地址服務常見問題",
                category="faq",
                is_active=True
            )
            chunk2 = KnowledgeChunk(
                content="地址服務價格資訊",
                category="service_info",
                is_active=True
            )
            db.add_all([chunk1, chunk2])
            await db.commit()

            service = RAGService()
            results = await service._keyword_search(
                db=db,
                query="地址",
                top_k=5,
                category="faq",  # 只要 faq 分類
                service_type=None
            )

            assert len(results) == 1
            assert results[0]["category"] == "faq"

    @pytest.mark.asyncio
    async def test_respects_top_k_limit(self, async_client):
        """測試結果數量限制"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            # 準備多筆測試資料
            for i in range(10):
                chunk = KnowledgeChunk(
                    content=f"測試內容 {i}",
                    category="test",
                    is_active=True
                )
                db.add(chunk)
            await db.commit()

            service = RAGService()
            results = await service._keyword_search(
                db=db,
                query="測試",
                top_k=3,  # 只要 3 筆
                category=None,
                service_type=None
            )

            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_excludes_inactive_chunks(self, async_client):
        """測試排除停用的知識"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            chunk_active = KnowledgeChunk(
                content="啟用的地址服務",
                category="service_info",
                is_active=True
            )
            chunk_inactive = KnowledgeChunk(
                content="停用的地址服務",
                category="service_info",
                is_active=False  # 停用
            )
            db.add_all([chunk_active, chunk_inactive])
            await db.commit()

            service = RAGService()
            results = await service._keyword_search(
                db=db,
                query="地址",
                top_k=10,
                category=None,
                service_type=None
            )

            assert len(results) == 1
            assert "啟用" in results[0]["content"]


class TestJsonVectorSearch:
    """測試 JSON 向量搜尋（SQLite 本地開發用）"""

    @pytest.mark.asyncio
    async def test_finds_similar_content(self, async_client):
        """
        測試向量相似度搜尋

        【情境】
        本地開發使用 SQLite，沒有 pgvector，
        所以把 embedding 存在 JSON 欄位，用 Python 計算相似度
        """
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            # 準備測試資料（帶 embedding）
            chunk = KnowledgeChunk(
                content="虛擬辦公室地址服務",
                category="service_info",
                embedding_json=[0.1, 0.2, 0.3, 0.4, 0.5],  # 模擬 embedding
                is_active=True
            )
            db.add(chunk)
            await db.commit()

            service = RAGService()

            # 使用相似的 embedding 搜尋
            query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # 完全相同 → 相似度 1.0
            results = await service._json_vector_search(
                db=db,
                query_embedding=query_embedding,
                top_k=5,
                category=None,
                service_type=None,
                similarity_threshold=0.7
            )

            assert len(results) == 1
            assert results[0]["similarity"] > 0.99  # 應該接近 1.0

    @pytest.mark.asyncio
    async def test_respects_similarity_threshold(self, async_client):
        """測試相似度門檻篩選"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            # 高相似度
            chunk_high = KnowledgeChunk(
                content="高相似度內容",
                category="test",
                embedding_json=[1.0, 0.0, 0.0],
                is_active=True
            )
            # 低相似度（正交向量）
            chunk_low = KnowledgeChunk(
                content="低相似度內容",
                category="test",
                embedding_json=[0.0, 1.0, 0.0],
                is_active=True
            )
            db.add_all([chunk_high, chunk_low])
            await db.commit()

            service = RAGService()
            query_embedding = [1.0, 0.0, 0.0]  # 與 high 相同，與 low 正交

            results = await service._json_vector_search(
                db=db,
                query_embedding=query_embedding,
                top_k=10,
                category=None,
                service_type=None,
                similarity_threshold=0.5  # 門檻 0.5
            )

            # 只有 high 應該通過門檻
            assert len(results) == 1
            assert results[0]["content"] == "高相似度內容"

    @pytest.mark.asyncio
    async def test_sorts_by_similarity(self, async_client):
        """測試結果按相似度排序"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            chunks = [
                KnowledgeChunk(
                    content="最相似",
                    category="test",
                    embedding_json=[1.0, 0.0, 0.0],
                    is_active=True
                ),
                KnowledgeChunk(
                    content="次相似",
                    category="test",
                    embedding_json=[0.8, 0.6, 0.0],  # cos(θ) ≈ 0.8
                    is_active=True
                ),
                KnowledgeChunk(
                    content="較不相似",
                    category="test",
                    embedding_json=[0.6, 0.8, 0.0],  # cos(θ) ≈ 0.6
                    is_active=True
                ),
            ]
            db.add_all(chunks)
            await db.commit()

            service = RAGService()
            query_embedding = [1.0, 0.0, 0.0]

            results = await service._json_vector_search(
                db=db,
                query_embedding=query_embedding,
                top_k=10,
                category=None,
                service_type=None,
                similarity_threshold=0.0
            )

            # 應該按相似度降序排列
            assert len(results) == 3
            assert results[0]["content"] == "最相似"
            assert results[0]["similarity"] > results[1]["similarity"]
            assert results[1]["similarity"] > results[2]["similarity"]


class TestSearchKnowledge:
    """測試主要搜尋入口（整合測試）"""

    @pytest.mark.asyncio
    async def test_uses_vector_search_when_embedding_available(self, async_client):
        """
        測試：有 embedding 時使用向量搜尋

        【流程】
        1. 呼叫 embedding_client 生成查詢向量
        2. 嘗試 pgvector 搜尋（會失敗，因為 SQLite 沒有 pgvector）
        3. 退回 JSON 向量搜尋
        """
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            # 準備測試資料
            chunk = KnowledgeChunk(
                content="測試向量搜尋",
                category="test",
                embedding_json=[0.5, 0.5, 0.5],
                is_active=True
            )
            db.add(chunk)
            await db.commit()

            # Mock embedding client
            service = RAGService()
            service.embedding_client = AsyncMock()
            service.embedding_client.embed_text = AsyncMock(
                return_value=[0.5, 0.5, 0.5]
            )

            results = await service.search_knowledge(
                db=db,
                query="測試",
                top_k=5
            )

            # 應該有結果（通過 JSON 向量搜尋）
            assert len(results) >= 1
            service.embedding_client.embed_text.assert_called_once_with("測試")

    @pytest.mark.asyncio
    async def test_falls_back_to_keyword_when_embedding_fails(self, async_client):
        """
        測試：embedding 失敗時退回關鍵字搜尋

        【為什麼重要】
        Embedding API 可能因為：
        - API key 無效
        - 網路問題
        - 額度用完
        而失敗。系統應該優雅降級，不是直接報錯。
        """
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            chunk = KnowledgeChunk(
                content="關鍵字搜尋測試",
                category="test",
                is_active=True
            )
            db.add(chunk)
            await db.commit()

            service = RAGService()
            # Mock embedding client 返回 None（表示失敗）
            service.embedding_client = AsyncMock()
            service.embedding_client.embed_text = AsyncMock(return_value=None)

            results = await service.search_knowledge(
                db=db,
                query="關鍵字",
                top_k=5
            )

            # 應該通過關鍵字搜尋找到結果
            assert len(results) == 1
            assert results[0]["similarity"] == 0.5  # 關鍵字搜尋的固定分數


class TestGetRelevantContext:
    """測試上下文格式化"""

    @pytest.mark.asyncio
    async def test_formats_context_by_category(self, async_client):
        """
        測試上下文格式化

        【輸出格式】
        ## 相關知識

        ### SPIN 問題庫
        - 問題 1
        - 問題 2

        ### 價值主張
        - 價值 1
        """
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            chunks = [
                KnowledgeChunk(
                    content="您是新設立還是變更地址？",
                    category="spin_question",
                    embedding_json=[0.5, 0.5],
                    is_active=True
                ),
                KnowledgeChunk(
                    content="24/7 代收信件服務",
                    category="value_prop",
                    embedding_json=[0.5, 0.5],
                    is_active=True
                ),
            ]
            db.add_all(chunks)
            await db.commit()

            service = RAGService()
            service.embedding_client = AsyncMock()
            service.embedding_client.embed_text = AsyncMock(
                return_value=[0.5, 0.5]
            )

            context = await service.get_relevant_context(db, "測試", top_k=10)

            assert "## 相關知識" in context
            assert "SPIN 問題庫" in context
            assert "價值主張" in context

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_results(self, async_client):
        """測試無結果時返回空字串"""
        from tests.conftest import TestSessionLocal

        async with TestSessionLocal() as db:
            service = RAGService()
            service.embedding_client = AsyncMock()
            service.embedding_client.embed_text = AsyncMock(return_value=None)

            context = await service.get_relevant_context(db, "完全無關的查詢")

            assert context == ""


class TestGetRagService:
    """測試單例模式"""

    def test_returns_same_instance(self):
        """
        測試單例模式

        【為什麼用單例】
        RAGService 內部持有 embedding_client，
        我們不想每次呼叫都重新初始化。
        """
        # 重置全域變數
        import services.rag_service as rag_module
        rag_module._rag_service = None

        service1 = get_rag_service()
        service2 = get_rag_service()

        assert service1 is service2, "應該返回同一個實例"
