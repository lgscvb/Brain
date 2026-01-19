"""
Migration 005: 新增意圖樹表（知識庫 DB 化）

【背景】
原本 logic_tree.json 是靜態檔案，有以下問題：
1. 更新需要重新部署
2. 無法追蹤變更歷史
3. 無法做 A/B 測試

【設計決策】
- intent_nodes: 樹狀結構存儲意圖節點
  - parent_id 指向父節點，形成樹狀結構
  - node_key 是唯一識別碼，對應原 JSON 的 id
  - keywords 和 spin_phases 用 JSON 儲存（SQLite 支援 JSON）

- spin_questions: 獨立儲存 SPIN 問題
  - 與 intent_node 是多對一關係
  - phase 是 S/P/I/N 其中一個
  - 可以針對不同服務類型有不同問題

【向後相容】
router.py 會根據設定決定資料來源：
- KNOWLEDGE_SOURCE=json: 使用 logic_tree.json（預設）
- KNOWLEDGE_SOURCE=database: 使用 DB
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "sqlite+aiosqlite:///brain.db"


async def migrate():
    """執行 migration"""
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        # ============================================================
        # 1. 建立 intent_nodes 表（意圖節點）
        # ============================================================
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS intent_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER REFERENCES intent_nodes(id) ON DELETE CASCADE,
                node_key VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                keywords JSON DEFAULT '[]',
                spin_phases JSON DEFAULT '[]',
                spin_guidance TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 索引：快速查找根節點
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_intent_nodes_parent
            ON intent_nodes (parent_id)
        """))

        # 索引：快速查找活躍節點
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_intent_nodes_active
            ON intent_nodes (is_active)
            WHERE is_active = TRUE
        """))

        print("✅ intent_nodes 表已建立")

        # ============================================================
        # 2. 建立 spin_questions 表（SPIN 問題庫）
        # ============================================================
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS spin_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_node_id INTEGER NOT NULL REFERENCES intent_nodes(id) ON DELETE CASCADE,
                phase CHAR(1) NOT NULL CHECK (phase IN ('S', 'P', 'I', 'N')),
                question TEXT NOT NULL,
                service_type VARCHAR(50),
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 索引：快速查找特定節點的問題
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_spin_questions_node
            ON spin_questions (intent_node_id, phase)
        """))

        # 索引：按服務類型篩選
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_spin_questions_service
            ON spin_questions (service_type)
            WHERE service_type IS NOT NULL
        """))

        print("✅ spin_questions 表已建立")

        # ============================================================
        # 3. 建立 spin_framework 表（SPIN 框架設定）
        # ============================================================
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS spin_framework (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phase CHAR(1) NOT NULL UNIQUE CHECK (phase IN ('S', 'P', 'I', 'N')),
                name VARCHAR(50) NOT NULL,
                name_zh VARCHAR(50) NOT NULL,
                purpose TEXT NOT NULL,
                signals_to_advance JSON DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0
            )
        """))

        print("✅ spin_framework 表已建立")

        # ============================================================
        # 4. 建立 spin_transition_rules 表（階段轉換規則）
        # ============================================================
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS spin_transition_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_phase VARCHAR(10) NOT NULL,
                to_phase CHAR(1) NOT NULL CHECK (to_phase IN ('S', 'P', 'I', 'N')),
                condition TEXT NOT NULL,
                trigger_keywords JSON DEFAULT '[]',
                is_active BOOLEAN DEFAULT TRUE,
                sort_order INTEGER DEFAULT 0
            )
        """))

        print("✅ spin_transition_rules 表已建立")

        print("\n✅ Migration 005 完成：意圖樹相關表已建立")


async def rollback():
    """回滾 migration"""
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS spin_transition_rules"))
        await conn.execute(text("DROP TABLE IF EXISTS spin_framework"))
        await conn.execute(text("DROP TABLE IF EXISTS spin_questions"))
        await conn.execute(text("DROP TABLE IF EXISTS intent_nodes"))

        print("✅ Migration 005 已回滾")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
