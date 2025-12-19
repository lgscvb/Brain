"""
測試 RAG 搜尋功能
"""
import asyncio
import sys
sys.path.insert(0, '/Users/daihaoting_1/Desktop/code/brain/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from services.rag_service import RAGService

# 資料庫連線
DATABASE_URL = "sqlite+aiosqlite:///brain.db"


async def main():
    """測試 RAG 搜尋"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    rag_service = RAGService()

    # 測試查詢
    test_queries = [
        "報價單怎麼轉成合約？",
        "續約流程是什麼？",
        "繳費狀態有哪些？",
        "新公司還沒有統編怎麼辦？",
        "會議室怎麼預約？",
    ]

    async with async_session() as session:
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"🔍 查詢: {query}")
            print('='*60)

            results = await rag_service.search_knowledge(
                db=session,
                query=query,
                top_k=3,
                similarity_threshold=0.5
            )

            if results:
                for i, r in enumerate(results, 1):
                    print(f"\n[{i}] 相似度: {r['similarity']:.3f}")
                    print(f"    分類: {r['category']} / {r.get('sub_category', 'N/A')}")
                    print(f"    內容: {r['content'][:100]}...")
            else:
                print("   ❌ 沒有找到相關結果")


if __name__ == "__main__":
    asyncio.run(main())
