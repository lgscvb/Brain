"""
Migration: 添加知識庫表和 pgvector 擴展
用於 RAG 系統的向量搜尋功能
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def run_migration(database_url: str):
    """
    執行 migration

    Args:
        database_url: 資料庫連接字串
    """
    # 將 postgresql:// 轉換為 postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        # 1. 啟用 pgvector 擴展
        print("1. 啟用 pgvector 擴展...")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("   ✅ pgvector 擴展已啟用")
        except Exception as e:
            print(f"   ⚠️ pgvector 擴展啟用失敗: {e}")
            print("   請確保已在 Cloud SQL 中安裝 pgvector 擴展")

        # 2. 建立 knowledge_chunks 表
        print("2. 建立 knowledge_chunks 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                sub_category VARCHAR(100),
                service_type VARCHAR(50),
                metadata JSONB,
                embedding_json JSONB,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        print("   ✅ knowledge_chunks 表已建立")

        # 3. 添加向量欄位（如果 pgvector 可用）
        print("3. 添加向量欄位...")
        try:
            # 檢查是否已存在 embedding 欄位
            result = await conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'knowledge_chunks'
                AND column_name = 'embedding'
            """))
            if result.fetchone() is None:
                await conn.execute(text("""
                    ALTER TABLE knowledge_chunks
                    ADD COLUMN embedding vector(1536)
                """))
                print("   ✅ embedding 向量欄位已添加")
            else:
                print("   ✅ embedding 向量欄位已存在")
        except Exception as e:
            print(f"   ⚠️ 向量欄位添加失敗: {e}")
            print("   將使用 embedding_json 作為備用")

        # 4. 建立索引
        print("4. 建立索引...")

        # 分類索引
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_category
            ON knowledge_chunks(category)
        """))

        # 服務類型索引
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_service_type
            ON knowledge_chunks(service_type)
        """))

        # 啟用狀態索引
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_is_active
            ON knowledge_chunks(is_active)
        """))

        # 向量索引（使用 IVFFlat，適合中小規模數據）
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding
                ON knowledge_chunks
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            print("   ✅ 向量索引已建立")
        except Exception as e:
            print(f"   ⚠️ 向量索引建立失敗: {e}")

        print("   ✅ 所有索引已建立")

    await engine.dispose()
    print("\n✅ Migration 完成!")


if __name__ == "__main__":
    import sys
    import os

    # 從環境變數或命令列參數獲取資料庫 URL
    database_url = os.getenv("DATABASE_URL")

    if len(sys.argv) > 1:
        database_url = sys.argv[1]

    if not database_url:
        print("請提供 DATABASE_URL 環境變數或命令列參數")
        print("用法: python 002_add_knowledge_chunks.py <database_url>")
        sys.exit(1)

    asyncio.run(run_migration(database_url))
