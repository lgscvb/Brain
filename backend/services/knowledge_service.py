"""
Brain - 知識庫服務

【用途】
提供意圖樹和 SPIN 問題的資料庫存取介面。

【主要功能】
1. get_intent_tree(): 取得完整意圖樹
2. get_root_nodes(): 取得根節點列表
3. get_spin_questions(): 取得 SPIN 問題
4. get_intent_node(): 取得特定節點
5. get_spin_framework(): 取得 SPIN 框架設定
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.models import IntentNode, SpinQuestion, SpinFramework, SpinTransitionRule


class KnowledgeService:
    """知識庫服務"""

    # ============================================================
    # 意圖樹操作
    # ============================================================

    async def get_root_nodes(self, db: AsyncSession) -> List[IntentNode]:
        """
        取得根節點列表（parent_id = NULL 的節點）

        Args:
            db: 資料庫 Session

        Returns:
            根節點列表，按 sort_order 排序
        """
        result = await db.execute(
            select(IntentNode)
            .where(IntentNode.parent_id.is_(None))
            .where(IntentNode.is_active == True)
            .order_by(IntentNode.sort_order)
            .options(selectinload(IntentNode.children))
        )
        return list(result.scalars().all())

    async def get_intent_node(
        self,
        db: AsyncSession,
        node_key: str
    ) -> Optional[IntentNode]:
        """
        取得特定意圖節點

        Args:
            db: 資料庫 Session
            node_key: 節點唯一識別碼

        Returns:
            IntentNode 或 None
        """
        result = await db.execute(
            select(IntentNode)
            .where(IntentNode.node_key == node_key)
            .where(IntentNode.is_active == True)
            .options(
                selectinload(IntentNode.children),
                selectinload(IntentNode.spin_questions)
            )
        )
        return result.scalar_one_or_none()

    async def get_intent_tree(self, db: AsyncSession) -> Dict:
        """
        取得完整意圖樹（遞迴建構）

        Args:
            db: 資料庫 Session

        Returns:
            樹狀結構的 dict，格式與 logic_tree.json 相容
        """
        root_nodes = await self.get_root_nodes(db)

        # 建構樹狀結構
        tree = {
            "root_nodes": [
                await self._build_node_dict(db, node)
                for node in root_nodes
            ]
        }

        return tree

    async def _build_node_dict(
        self,
        db: AsyncSession,
        node: IntentNode
    ) -> Dict:
        """
        遞迴建構節點 dict（含子節點）

        Args:
            db: 資料庫 Session
            node: IntentNode 物件

        Returns:
            節點 dict，格式與 logic_tree.json 相容
        """
        # 取得此節點的 SPIN 問題
        spin_questions = await self.get_spin_questions_for_node(db, node.id)

        # 建構節點 dict
        node_dict = {
            "id": node.node_key,
            "name": node.name,
            "keywords": node.keywords or [],
            "spin_phase": node.spin_phases or [],
        }

        # 加入 SPIN 指引（如果有）
        if node.spin_guidance:
            node_dict["spin_guidance"] = node.spin_guidance

        # 加入 SPIN 問題（如果有）
        if spin_questions:
            node_dict["spin_questions"] = spin_questions

        # 遞迴處理子節點
        if node.children:
            # 需要重新載入子節點以取得完整資訊
            children_result = await db.execute(
                select(IntentNode)
                .where(IntentNode.parent_id == node.id)
                .where(IntentNode.is_active == True)
                .order_by(IntentNode.sort_order)
                .options(selectinload(IntentNode.children))
            )
            children = list(children_result.scalars().all())

            if children:
                node_dict["children"] = [
                    await self._build_node_dict(db, child)
                    for child in children
                ]

        return node_dict

    # ============================================================
    # SPIN 問題操作
    # ============================================================

    async def get_spin_questions_for_node(
        self,
        db: AsyncSession,
        node_id: int
    ) -> Dict[str, List[str]]:
        """
        取得特定節點的 SPIN 問題（按階段分組）

        Args:
            db: 資料庫 Session
            node_id: 節點 ID

        Returns:
            Dict[phase, List[question]]，如 {"S": ["問題1", "問題2"], "P": [...]}
        """
        result = await db.execute(
            select(SpinQuestion)
            .where(SpinQuestion.intent_node_id == node_id)
            .where(SpinQuestion.is_active == True)
            .order_by(SpinQuestion.phase, SpinQuestion.sort_order)
        )
        questions = result.scalars().all()

        # 按階段分組
        grouped: Dict[str, List[str]] = {}
        for q in questions:
            if q.phase not in grouped:
                grouped[q.phase] = []
            grouped[q.phase].append(q.question)

        return grouped

    async def get_spin_questions(
        self,
        db: AsyncSession,
        phase: str,
        service_type: Optional[str] = None,
        limit: int = 5
    ) -> List[str]:
        """
        取得特定階段的 SPIN 問題

        Args:
            db: 資料庫 Session
            phase: SPIN 階段（S/P/I/N）
            service_type: 服務類型（可選）
            limit: 回傳數量上限

        Returns:
            問題列表
        """
        query = (
            select(SpinQuestion)
            .where(SpinQuestion.phase == phase)
            .where(SpinQuestion.is_active == True)
        )

        if service_type:
            query = query.where(
                (SpinQuestion.service_type == service_type) |
                (SpinQuestion.service_type.is_(None))
            )

        query = query.order_by(SpinQuestion.sort_order).limit(limit)

        result = await db.execute(query)
        questions = result.scalars().all()

        return [q.question for q in questions]

    # ============================================================
    # SPIN 框架操作
    # ============================================================

    async def get_spin_framework(self, db: AsyncSession) -> Dict:
        """
        取得 SPIN 框架設定

        Args:
            db: 資料庫 Session

        Returns:
            SPIN 框架 dict
        """
        # 取得階段定義
        phases_result = await db.execute(
            select(SpinFramework)
            .where(SpinFramework.is_active == True)
            .order_by(SpinFramework.sort_order)
        )
        phases = phases_result.scalars().all()

        # 取得轉換規則
        rules_result = await db.execute(
            select(SpinTransitionRule)
            .where(SpinTransitionRule.is_active == True)
            .order_by(SpinTransitionRule.sort_order)
        )
        rules = rules_result.scalars().all()

        return {
            "phases": {
                p.phase: {
                    "name": p.name,
                    "name_zh": p.name_zh,
                    "purpose": p.purpose,
                    "signals_to_advance": p.signals_to_advance or []
                }
                for p in phases
            },
            "transition_rules": [
                {
                    "from": r.from_phase,
                    "to": r.to_phase,
                    "condition": r.condition,
                    "trigger_keywords": r.trigger_keywords or []
                }
                for r in rules
            ]
        }


# 全域實例
_knowledge_service: Optional[KnowledgeService] = None


def get_knowledge_service() -> KnowledgeService:
    """取得知識庫服務單例"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
