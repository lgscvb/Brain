"""
Migration 004: 新增 Prompt 版本管理表

【為什麼需要 Prompt 版本管理】
1. 追蹤變更：知道誰在什麼時候改了什麼
2. 快速回滾：新版本效果不好？一鍵切回舊版
3. A/B 測試：可以同時準備多個版本，快速切換測試
4. 審計軌跡：合規需求，記錄所有變更歷史

【設計決策】
- prompt_key: 識別不同用途的 prompt（如 draft_prompt, router_prompt）
- version: 同一 key 的版本號，從 1 開始遞增
- is_active: 每個 key 只能有一個活躍版本
- content: 實際的 prompt 內容
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "sqlite+aiosqlite:///brain.db"


async def migrate():
    """執行 migration"""
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # 建立 Prompt 版本表
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_key VARCHAR(50) NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                description VARCHAR(500),
                is_active BOOLEAN DEFAULT FALSE,
                created_by VARCHAR(100) DEFAULT 'system',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (prompt_key, version)
            )
        """))

        # 建立索引：快速查找活躍版本
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prompt_active
            ON prompt_versions (prompt_key, is_active)
            WHERE is_active = TRUE
        """))

        print("✅ Migration 004 完成：prompt_versions 表已建立")


async def seed_initial_prompts():
    """
    Seed 初始 Prompt 版本

    【注意】
    這個函數只在首次部署時執行一次
    之後的 prompt 更新應該透過 Admin API
    """
    from brain.prompts import (
        SECURITY_RULES,
        DRAFT_PROMPT,
        DRAFT_PROMPT_FALLBACK,
        ROUTER_PROMPT,
        MODIFICATION_ANALYSIS_PROMPT
    )

    engine = create_async_engine(DATABASE_URL, echo=True)

    initial_prompts = [
        ("security_rules", SECURITY_RULES, "安全防護規則 - 注入到所有 Prompt"),
        ("draft_prompt", DRAFT_PROMPT, "草稿生成 Prompt（含 RAG）"),
        ("draft_prompt_fallback", DRAFT_PROMPT_FALLBACK, "草稿生成 Prompt（無 RAG 備用）"),
        ("router_prompt", ROUTER_PROMPT, "LLM Routing 分流 Prompt"),
        ("modification_analysis_prompt", MODIFICATION_ANALYSIS_PROMPT, "修改分析 Prompt"),
    ]

    async with engine.begin() as conn:
        for prompt_key, content, description in initial_prompts:
            # 檢查是否已存在
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM prompt_versions WHERE prompt_key = :key"
            ), {"key": prompt_key})
            count = result.scalar()

            if count == 0:
                await conn.execute(text("""
                    INSERT INTO prompt_versions (prompt_key, version, content, description, is_active, created_by)
                    VALUES (:key, 1, :content, :description, TRUE, 'system')
                """), {
                    "key": prompt_key,
                    "content": content,
                    "description": description
                })
                print(f"  ✅ 已建立 {prompt_key} v1")
            else:
                print(f"  ⏭️ {prompt_key} 已存在，跳過")

        print("✅ 初始 Prompt 版本已 Seed 完成")


if __name__ == "__main__":
    asyncio.run(migrate())
    # 可選：執行 seed
    # asyncio.run(seed_initial_prompts())
