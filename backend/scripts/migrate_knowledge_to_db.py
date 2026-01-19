"""
知識庫遷移腳本：JSON → DB

【用途】
將 logic_tree.json 的資料遷移到資料庫，包括：
1. intent_nodes（意圖節點）
2. spin_questions（SPIN 問題）
3. spin_framework（SPIN 框架定義）
4. spin_transition_rules（階段轉換規則）

【使用方式】
cd backend
python scripts/migrate_knowledge_to_db.py           # 執行遷移
python scripts/migrate_knowledge_to_db.py --verify  # 驗證遷移結果
python scripts/migrate_knowledge_to_db.py --dry-run # 只顯示會做什麼，不實際執行

【注意事項】
1. 遷移前會檢查是否已有資料，避免重複執行
2. 使用 transaction，確保資料一致性
3. 遷移後會輸出統計資訊
"""
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# 添加 parent 目錄到 path，以便 import db models
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.models import Base, IntentNode, SpinQuestion, SpinFramework, SpinTransitionRule

DATABASE_URL = "sqlite+aiosqlite:///brain.db"


class KnowledgeMigrator:
    """知識庫遷移器"""

    def __init__(self, json_path: str, dry_run: bool = False):
        self.json_path = Path(json_path)
        self.dry_run = dry_run
        self.stats = {
            "intent_nodes": 0,
            "spin_questions": 0,
            "spin_framework": 0,
            "transition_rules": 0
        }

    async def run(self):
        """執行遷移"""
        # 讀取 JSON
        print(f"\n📖 讀取 {self.json_path}...")
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logic_tree = data.get("logic_tree", {})
        root_nodes = logic_tree.get("root_nodes", [])
        spin_framework = logic_tree.get("spin_framework", {})

        print(f"  ✅ 找到 {len(root_nodes)} 個根節點")

        if self.dry_run:
            print("\n⚠️ Dry run 模式：只顯示會做什麼，不實際執行\n")
            self._dry_run_nodes(root_nodes)
            return

        # 建立資料庫連線
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            async with session.begin():
                # 檢查是否已有資料
                existing = await session.execute(
                    select(IntentNode).limit(1)
                )
                if existing.scalar():
                    print("\n⚠️ 資料庫已有意圖節點資料")
                    confirm = input("是否要清除並重新遷移？(y/N): ")
                    if confirm.lower() != 'y':
                        print("❌ 取消遷移")
                        return
                    # 清除現有資料
                    await session.execute(text("DELETE FROM spin_questions"))
                    await session.execute(text("DELETE FROM intent_nodes"))
                    await session.execute(text("DELETE FROM spin_framework"))
                    await session.execute(text("DELETE FROM spin_transition_rules"))
                    print("  🗑️ 已清除現有資料")

                # 遷移 SPIN 框架定義
                await self._migrate_spin_framework(session, spin_framework)

                # 遷移意圖節點（遞迴）
                for idx, node in enumerate(root_nodes):
                    await self._migrate_node(session, node, parent_id=None, sort_order=idx)

        print("\n" + "=" * 50)
        print("✅ 遷移完成！")
        print(f"  - 意圖節點：{self.stats['intent_nodes']} 個")
        print(f"  - SPIN 問題：{self.stats['spin_questions']} 個")
        print(f"  - SPIN 框架：{self.stats['spin_framework']} 個")
        print(f"  - 轉換規則：{self.stats['transition_rules']} 個")

    def _dry_run_nodes(self, nodes: List[Dict], depth: int = 0):
        """Dry run：顯示節點結構"""
        for node in nodes:
            indent = "  " * depth
            node_id = node.get("id", "?")
            name = node.get("name", "?")
            keywords = node.get("keywords", [])
            spin_questions = node.get("spin_questions", {})

            print(f"{indent}📁 {name} ({node_id})")
            if keywords:
                print(f"{indent}   關鍵字: {keywords[:3]}{'...' if len(keywords) > 3 else ''}")
            if spin_questions:
                for phase, questions in spin_questions.items():
                    print(f"{indent}   {phase}: {len(questions)} 個問題")

            children = node.get("children", [])
            if children:
                self._dry_run_nodes(children, depth + 1)

    async def _migrate_spin_framework(self, session: AsyncSession, framework: Dict):
        """遷移 SPIN 框架定義"""
        phases = framework.get("phases", {})
        transition_rules = framework.get("transition_rules", [])

        print("\n📦 遷移 SPIN 框架...")

        # 遷移階段定義
        for idx, (phase, info) in enumerate(phases.items()):
            spin_phase = SpinFramework(
                phase=phase,
                name=info.get("name", ""),
                name_zh=info.get("name_zh", ""),
                purpose=info.get("purpose", ""),
                signals_to_advance=info.get("signals_to_advance", []),
                is_active=True,
                sort_order=idx
            )
            session.add(spin_phase)
            self.stats["spin_framework"] += 1
            print(f"  ✅ {phase}: {info.get('name_zh', '')}")

        # 遷移轉換規則
        for idx, rule in enumerate(transition_rules):
            transition = SpinTransitionRule(
                from_phase=rule.get("from", ""),
                to_phase=rule.get("to", ""),
                condition=rule.get("condition", ""),
                trigger_keywords=rule.get("trigger_keywords", []),
                is_active=True,
                sort_order=idx
            )
            session.add(transition)
            self.stats["transition_rules"] += 1

        print(f"  ✅ {len(transition_rules)} 個轉換規則")

    async def _migrate_node(
        self,
        session: AsyncSession,
        node: Dict,
        parent_id: Optional[int],
        sort_order: int = 0
    ) -> int:
        """
        遞迴遷移意圖節點

        Args:
            session: 資料庫 session
            node: 節點資料
            parent_id: 父節點 ID
            sort_order: 排序順序

        Returns:
            新建立的節點 ID
        """
        node_key = node.get("id", f"node_{self.stats['intent_nodes']}")
        name = node.get("name", "未命名")

        # 建立意圖節點
        intent_node = IntentNode(
            parent_id=parent_id,
            node_key=node_key,
            name=name,
            keywords=node.get("keywords", []),
            spin_phases=node.get("spin_phase", []),
            spin_guidance=node.get("spin_guidance"),
            is_active=True,
            sort_order=sort_order
        )
        session.add(intent_node)
        await session.flush()  # 取得自動生成的 ID

        self.stats["intent_nodes"] += 1
        print(f"  {'  ' * (1 if parent_id else 0)}📁 {name} (id={intent_node.id})")

        # 遷移 SPIN 問題
        spin_questions = node.get("spin_questions", {})
        for phase, questions in spin_questions.items():
            for q_idx, question in enumerate(questions):
                spin_q = SpinQuestion(
                    intent_node_id=intent_node.id,
                    phase=phase,
                    question=question,
                    is_active=True,
                    sort_order=q_idx
                )
                session.add(spin_q)
                self.stats["spin_questions"] += 1

        # 遞迴處理子節點
        children = node.get("children", [])
        for idx, child in enumerate(children):
            await self._migrate_node(session, child, intent_node.id, idx)

        return intent_node.id


async def verify_migration():
    """驗證遷移結果"""
    print("\n🔍 驗證遷移結果...\n")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 統計各表資料數量
        intent_count = (await session.execute(
            select(IntentNode)
        )).scalars().all()
        spin_q_count = (await session.execute(
            select(SpinQuestion)
        )).scalars().all()
        framework_count = (await session.execute(
            select(SpinFramework)
        )).scalars().all()
        rule_count = (await session.execute(
            select(SpinTransitionRule)
        )).scalars().all()

        print("📊 資料庫統計：")
        print(f"  - intent_nodes: {len(intent_count)} 筆")
        print(f"  - spin_questions: {len(spin_q_count)} 筆")
        print(f"  - spin_framework: {len(framework_count)} 筆")
        print(f"  - spin_transition_rules: {len(rule_count)} 筆")

        # 顯示根節點
        root_nodes = await session.execute(
            select(IntentNode)
            .where(IntentNode.parent_id.is_(None))
            .order_by(IntentNode.sort_order)
        )
        roots = root_nodes.scalars().all()

        print(f"\n📁 根節點 ({len(roots)} 個)：")
        for node in roots:
            children_count = await session.execute(
                select(IntentNode)
                .where(IntentNode.parent_id == node.id)
            )
            children = children_count.scalars().all()
            print(f"  - {node.name} ({node.node_key}): {len(children)} 個子節點")


async def main():
    parser = argparse.ArgumentParser(description="知識庫遷移腳本")
    parser.add_argument("--verify", action="store_true", help="驗證遷移結果")
    parser.add_argument("--dry-run", action="store_true", help="只顯示會做什麼，不實際執行")
    parser.add_argument(
        "--json-path",
        default=str(Path(__file__).parent.parent.parent / "logic_tree.json"),
        help="logic_tree.json 路徑"
    )
    args = parser.parse_args()

    if args.verify:
        await verify_migration()
    else:
        migrator = KnowledgeMigrator(args.json_path, dry_run=args.dry_run)
        await migrator.run()


if __name__ == "__main__":
    asyncio.run(main())
