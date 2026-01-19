"""
Brain - 意圖路由器
使用 logic_tree.json 或資料庫進行意圖分類

【資料來源切換】
透過 config.KNOWLEDGE_SOURCE 設定：
- "json": 使用 logic_tree.json（預設，向後相容）
- "database": 使用資料庫（需先執行 migrate_knowledge_to_db.py）

【DB 模式注意事項】
DB 模式下需要傳入 db session，使用 classify_intent_async() 方法
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

from config import settings


class IntentRouter:
    """
    意圖路由器

    【使用方式】
    # JSON 模式（同步）
    router = IntentRouter()
    result = router.classify_intent("我想租辦公室")

    # DB 模式（非同步）
    from services.knowledge_service import get_knowledge_service
    service = get_knowledge_service()
    result = await service.classify_intent(db, "我想租辦公室")
    """

    def __init__(self):
        """載入 logic_tree.json（JSON 模式用）"""
        self.source = settings.KNOWLEDGE_SOURCE

        if self.source == "json":
            self._load_json()
        else:
            # DB 模式：延遲載入，由 KnowledgeService 處理
            self.logic_tree = {}
            self.root_nodes = []
            print(f"📦 IntentRouter: 使用 DB 模式，請透過 KnowledgeService 存取")

    def _load_json(self):
        """載入 logic_tree.json"""
        logic_tree_path = Path(__file__).parent.parent.parent / "logic_tree.json"

        try:
            with open(logic_tree_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.logic_tree = data.get("logic_tree", {})
                self.root_nodes = self.logic_tree.get("root_nodes", [])
                print(f"📖 IntentRouter: 從 JSON 載入 {len(self.root_nodes)} 個根節點")
        except FileNotFoundError:
            print(f"⚠️ 警告：找不到 logic_tree.json，使用空白邏輯樹")
            self.logic_tree = {}
            self.root_nodes = []
    
    def classify_intent(self, message: str) -> Dict:
        """
        分類訊息意圖
        
        Args:
            message: 客戶訊息
        
        Returns:
            {
                "intent": "主要意圖",
                "sub_intent": "子意圖",
                "matched_keywords": ["匹配的關鍵字"],
                "confidence": 0.8
            }
        """
        message_lower = message.lower()
        best_match = {
            "intent": "其他",
            "sub_intent": None,
            "matched_keywords": [],
            "confidence": 0.0
        }
        
        # 遍歷根節點
        for root_node in self.root_nodes:
            result = self._match_node(root_node, message_lower)
            if result["confidence"] > best_match["confidence"]:
                best_match = result
        
        return best_match
    
    def _match_node(self, node: Dict, message: str, parent_name: str = None) -> Dict:
        """
        遞迴匹配節點
        
        Args:
            node: 節點資料
            message: 訊息內容（小寫）
            parent_name: 父節點名稱
        
        Returns:
            匹配結果
        """
        node_name = node.get("name", "")
        keywords = node.get("keywords", [])
        
        # 計算關鍵字匹配數
        matched_keywords = [kw for kw in keywords if kw.lower() in message]
        match_count = len(matched_keywords)
        
        # 計算信心度（匹配關鍵字數 / 總關鍵字數）
        confidence = match_count / len(keywords) if keywords else 0.0
        
        result = {
            "intent": parent_name or node_name,
            "sub_intent": node_name if parent_name else None,
            "matched_keywords": matched_keywords,
            "confidence": confidence
        }
        
        # 如果有子節點，遞迴尋找更精確的匹配
        children = node.get("children", [])
        if children:
            best_child_match = result
            for child in children:
                child_result = self._match_node(
                    child,
                    message,
                    parent_name or node_name
                )
                if child_result["confidence"] > best_child_match["confidence"]:
                    best_child_match = child_result
            
            # 如果子節點匹配度更高，使用子節點結果
            if best_child_match["confidence"] > confidence:
                return best_child_match
        
        return result
    
    def get_intent_info(self, intent_name: str) -> Optional[Dict]:
        """
        取得意圖詳細資訊
        
        Args:
            intent_name: 意圖名稱
        
        Returns:
            意圖資訊或 None
        """
        for root_node in self.root_nodes:
            result = self._find_node_by_name(root_node, intent_name)
            if result:
                return result
        return None
    
    def _find_node_by_name(self, node: Dict, name: str) -> Optional[Dict]:
        """遞迴尋找指定名稱的節點"""
        if node.get("name") == name:
            return node
        
        children = node.get("children", [])
        for child in children:
            result = self._find_node_by_name(child, name)
            if result:
                return result
        
        return None


# 全域意圖路由器實例
_intent_router: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """取得意圖路由器單例"""
    global _intent_router
    if _intent_router is None:
        _intent_router = IntentRouter()
    return _intent_router
