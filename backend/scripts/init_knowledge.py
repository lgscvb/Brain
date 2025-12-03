"""
Brain - 知識庫初始化腳本
從 JSON 文件解析並匯入知識到資料庫
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加專案根目錄到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import Base, KnowledgeChunk
from services.embedding_client import get_embedding_client
from config import settings


class KnowledgeImporter:
    """知識庫匯入器"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.embedding_client = get_embedding_client()
        self.imported_count = 0
        self.skipped_count = 0

    async def import_from_sales_mindmap(self, file_path: str) -> int:
        """
        從 sales_mindmap.json 匯入知識

        解析結構：
        - spin_framework.phases.{S,P,I,N}.question_bank -> spin_question
        - service_types[].components[].items -> value_prop, objection, etc.
        - general_techniques[].tactics -> tactics
        """
        print(f"\n📚 正在匯入 sales_mindmap.json...")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        mindmap = data.get("sales_mindmap", {})

        # 1. 匯入 SPIN 問題庫
        await self._import_spin_questions(mindmap.get("spin_framework", {}).get("phases", {}))

        # 2. 匯入服務類型相關內容
        await self._import_service_content(mindmap.get("service_types", []))

        # 3. 匯入通用技巧
        await self._import_techniques(mindmap.get("general_techniques", []))

        # 4. 匯入常見情境
        await self._import_scenarios(mindmap.get("spin_framework", {}).get("common_scenarios", []))

        return self.imported_count

    async def _import_spin_questions(self, phases: Dict):
        """匯入 SPIN 各階段問題"""
        phase_names = {
            "S": "Situation",
            "P": "Problem",
            "I": "Implication",
            "N": "Need-payoff"
        }

        for phase_key, phase_data in phases.items():
            phase_name = phase_names.get(phase_key, phase_key)
            question_bank = phase_data.get("question_bank", {})

            for question_type, questions in question_bank.items():
                for question in questions:
                    await self._add_chunk(
                        content=question,
                        category="spin_question",
                        sub_category=phase_key,
                        metadata={
                            "phase_name": phase_name,
                            "question_type": question_type,
                            "purpose": phase_data.get("purpose", ""),
                            "tone": phase_data.get("tone", "")
                        }
                    )

    async def _import_service_content(self, service_types: List):
        """匯入服務相關內容"""
        for service in service_types:
            service_id = service.get("id", "")
            service_name = service.get("name", "")

            for component in service.get("components", []):
                component_type = component.get("type", "")

                # 映射到我們的分類
                category_map = {
                    "value_statement": "value_prop",
                    "differentiation": "value_prop",
                    "concern_handling": "objection",
                    "call_to_action": "value_prop"
                }
                category = category_map.get(component_type, "service_info")

                for item in component.get("items", []):
                    await self._add_chunk(
                        content=item.get("content", ""),
                        category=category,
                        sub_category=component_type,
                        service_type=service_id,
                        metadata={
                            "service_name": service_name,
                            "item_id": item.get("id", ""),
                            "usage_context": item.get("usage_context", []),
                            "spin_phase": item.get("spin_phase", "")
                        }
                    )

    async def _import_techniques(self, techniques: List):
        """匯入銷售技巧"""
        for technique in techniques:
            technique_name = technique.get("name", "")

            for tactic in technique.get("tactics", []):
                await self._add_chunk(
                    content=tactic.get("content", ""),
                    category="tactics",
                    sub_category=technique.get("id", ""),
                    metadata={
                        "technique_name": technique_name,
                        "spin_alignment": technique.get("spin_alignment", ""),
                        "usage_context": tactic.get("usage_context", []),
                        "spin_note": tactic.get("spin_note", "")
                    }
                )

    async def _import_scenarios(self, scenarios: List):
        """匯入常見情境"""
        for scenario in scenarios:
            # 情境描述
            await self._add_chunk(
                content=f"情境：{scenario.get('scenario', '')}\n回覆範例：{scenario.get('example_response', '')}",
                category="scenario",
                sub_category=scenario.get("spin_approach", ""),
                metadata={
                    "next_questions": scenario.get("next_questions", [])
                }
            )

    async def import_from_logic_tree(self, file_path: str) -> int:
        """
        從 logic_tree.json 匯入知識

        解析結構：
        - root_nodes[].children[...].spin_questions -> spin_question
        """
        print(f"\n📚 正在匯入 logic_tree.json...")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logic_tree = data.get("logic_tree", {})

        # 遞迴匯入所有節點的 SPIN 問題
        await self._import_tree_nodes(logic_tree.get("root_nodes", []))

        return self.imported_count

    async def _import_tree_nodes(self, nodes: List, parent_name: str = ""):
        """遞迴匯入樹狀結構的節點"""
        for node in nodes:
            node_name = node.get("name", "")
            node_id = node.get("id", "")
            service_type = None

            # 判斷服務類型
            if "address" in node_id or "登記" in node_name:
                service_type = "address_service"
            elif "coworking" in node_id or "共享" in node_name:
                service_type = "coworking"
            elif "office" in node_id or "辦公室" in node_name:
                service_type = "private_office"

            # 匯入此節點的 SPIN 問題
            spin_questions = node.get("spin_questions", {})
            for phase, questions in spin_questions.items():
                for question in questions:
                    await self._add_chunk(
                        content=question,
                        category="spin_question",
                        sub_category=phase,
                        service_type=service_type,
                        metadata={
                            "node_id": node_id,
                            "node_name": node_name,
                            "parent": parent_name,
                            "keywords": node.get("keywords", [])
                        }
                    )

            # 遞迴處理子節點
            children = node.get("children", [])
            if children:
                await self._import_tree_nodes(children, node_name)

    async def import_from_training_data(self, file_path: str, limit: int = 50) -> int:
        """
        從 training_data.json 匯入對話範例

        Args:
            file_path: 文件路徑
            limit: 最大匯入數量
        """
        print(f"\n📚 正在匯入 training_data.json (限制 {limit} 則)...")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        conversations = data.get("conversations", [])

        count = 0
        for conv in conversations[:limit]:
            topic = conv.get("topic", "")
            tags = conv.get("tags", [])

            for turn in conv.get("turns", []):
                if turn.get("role") == "assistant":
                    content = turn.get("content", "")
                    await self._add_chunk(
                        content=f"[{topic}] {content}",
                        category="example_response",
                        sub_category=turn.get("dialog_act", ""),
                        metadata={
                            "conversation_id": conv.get("conversation_id", ""),
                            "topic": topic,
                            "tags": tags,
                            "strategy": turn.get("strategy", "")
                        }
                    )
                    count += 1

        print(f"   匯入了 {count} 則對話範例")
        return count

    async def _add_chunk(
        self,
        content: str,
        category: str,
        sub_category: str = None,
        service_type: str = None,
        metadata: Dict = None
    ):
        """添加單個知識 chunk"""
        if not content or len(content.strip()) < 5:
            self.skipped_count += 1
            return

        # 檢查是否已存在（避免重複）
        from sqlalchemy import select
        existing = await self.session.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.content == content,
                KnowledgeChunk.category == category
            )
        )
        if existing.scalar_one_or_none():
            self.skipped_count += 1
            return

        # 生成 Embedding
        embedding = await self.embedding_client.embed_text(content)

        chunk = KnowledgeChunk(
            content=content,
            category=category,
            sub_category=sub_category,
            service_type=service_type,
            extra_data=metadata or {},
            embedding_json=embedding,
            is_active=True
        )

        self.session.add(chunk)
        self.imported_count += 1

        # 每 50 個提交一次
        if self.imported_count % 50 == 0:
            await self.session.commit()
            print(f"   已匯入 {self.imported_count} 條...")


async def main():
    """主函數"""
    print("=" * 60)
    print("Brain 知識庫初始化工具")
    print("=" * 60)

    # 資料庫連接
    database_url = settings.DATABASE_URL
    # 轉換為 async driver（如果還沒有）
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("sqlite://") and "+aiosqlite" not in database_url:
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    # 如果已經是 sqlite+aiosqlite:// 則不需要轉換

    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 建立表（如果不存在）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 找到 JSON 文件（支援多種路徑）
    def find_json_file(filename: str) -> Path:
        """搜尋 JSON 檔案，支援本地開發和 Docker 環境"""
        search_paths = [
            Path(__file__).parent.parent.parent / filename,  # 本地: brain/
            Path(__file__).parent.parent / filename,          # Docker: /app/
            Path.cwd() / filename,                            # 當前目錄
            Path.cwd().parent / filename,                     # 父目錄
        ]
        for path in search_paths:
            if path.exists():
                return path
        return search_paths[0]  # 回傳第一個路徑用於錯誤訊息

    sales_mindmap_path = find_json_file("sales_mindmap.json")
    logic_tree_path = find_json_file("logic_tree.json")
    training_data_path = find_json_file("training_data.json")

    async with async_session() as session:
        importer = KnowledgeImporter(session)

        # 匯入 sales_mindmap.json
        if sales_mindmap_path.exists():
            await importer.import_from_sales_mindmap(str(sales_mindmap_path))
        else:
            print(f"⚠️ 找不到 {sales_mindmap_path}")

        # 匯入 logic_tree.json
        if logic_tree_path.exists():
            await importer.import_from_logic_tree(str(logic_tree_path))
        else:
            print(f"⚠️ 找不到 {logic_tree_path}")

        # 匯入 training_data.json（限制數量）
        if training_data_path.exists():
            await importer.import_from_training_data(str(training_data_path), limit=30)
        else:
            print(f"⚠️ 找不到 {training_data_path}")

        # 最終提交
        await session.commit()

        print("\n" + "=" * 60)
        print(f"✅ 匯入完成!")
        print(f"   - 成功匯入: {importer.imported_count} 條")
        print(f"   - 略過（重複/空白）: {importer.skipped_count} 條")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
