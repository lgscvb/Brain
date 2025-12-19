"""
Migration 003: 新增草稿修正對話表
用於追蹤多輪對話修正歷史，支援訓練資料匯出
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "sqlite+aiosqlite:///brain.db"


async def migrate():
    """執行 migration"""
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # 建立草稿修正表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS draft_refinements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL DEFAULT 1,
                instruction TEXT NOT NULL,
                original_content TEXT NOT NULL,
                refined_content TEXT NOT NULL,
                model_used VARCHAR(100),
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                is_accepted BOOLEAN DEFAULT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (draft_id) REFERENCES drafts(id)
            )
        """))

        # 建立訓練資料匯出表（記錄匯出歷史）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS training_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_type VARCHAR(20) NOT NULL,
                record_count INTEGER NOT NULL,
                file_path VARCHAR(500),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

        print("✅ Migration 003 完成：draft_refinements 和 training_exports 表已建立")


if __name__ == "__main__":
    asyncio.run(migrate())
