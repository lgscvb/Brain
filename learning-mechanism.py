# learning/modification_analyzer.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import difflib

class ModificationType(Enum):
    TONE = "tone"                    # 語氣調整
    ACCURACY = "accuracy"            # 資訊正確性
    LENGTH = "length"                # 長度調整
    STRUCTURE = "structure"          # 結構調整
    ADD_INFO = "add_info"            # 新增資訊
    REMOVE_INFO = "remove_info"      # 移除資訊
    STYLE = "style"                  # 風格調整
    EMOJI = "emoji"                  # 表情符號
    PERSONALIZATION = "personalization"  # 個人化
    SPIN_STAGE = "spin_stage"        # SPIN 階段調整
    CTA = "cta"                      # 行動呼籲調整
    OTHER = "other"

@dataclass
class ModificationAnalysis:
    original: str
    modified: str
    diff_summary: str
    diff_detail: list
    modification_types: list[ModificationType]
    ai_reason: str
    suggested_prompt_update: Optional[str]
    confidence: float

class ModificationAnalyzer:
    """分析人類修改，提取學習信號"""
    
    ANALYSIS_PROMPT = """
你是一個專門分析「人類如何修改 AI 草稿」的專家。

## 原始 AI 草稿
{original}

## 人類修改後版本
{modified}

## 差異摘要
{diff}

## 對話情境
- 客戶類型：{customer_type}
- 對話階段：{conversation_stage}
- 訊息來源：{source}

## 請分析

1. **修改類型**（可多選）
   - tone: 語氣調整（更正式/更親切/更專業）
   - accuracy: 資訊正確性修正
   - length: 長度調整（太長/太短）
   - structure: 結構重組
   - add_info: 新增資訊
   - remove_info: 移除不必要內容
   - style: 風格調整
   - emoji: 表情符號增減
   - personalization: 增加個人化元素
   - spin_stage: SPIN 銷售階段調整
   - cta: 行動呼籲調整
   - other: 其他

2. **為什麼人類這樣改？**
   分析修改背後的意圖和原因

3. **這反映什麼偏好？**
   - 這位操作者的個人風格偏好
   - 這類客戶/情境的最佳實踐
   - AI prompt 應該如何調整

4. **建議的 Prompt 更新**
   如果要讓 AI 下次直接產出更好的草稿，prompt 應該加什麼指示？

## 回傳 JSON
{{
    "modification_types": ["type1", "type2"],
    "reason_analysis": "為什麼這樣改的分析",
    "operator_preference": "操作者偏好",
    "context_best_practice": "此情境的最佳實踐",
    "suggested_prompt_addition": "建議加入 prompt 的指示",
    "confidence": 0.0-1.0,
    "key_insight": "最重要的一個學習點"
}}
"""

    async def analyze(
        self, 
        original: str, 
        modified: str,
        context: dict
    ) -> ModificationAnalysis:
        """分析修改並提取學習信號"""
        
        # 1. 計算文字差異
        diff_detail = list(difflib.unified_diff(
            original.splitlines(), 
            modified.splitlines(),
            lineterm=''
        ))
        diff_summary = self._summarize_diff(original, modified)
        
        # 2. 讓 AI 分析修改原因
        analysis = await self._ai_analyze(original, modified, diff_summary, context)
        
        # 3. 建構結果
        return ModificationAnalysis(
            original=original,
            modified=modified,
            diff_summary=diff_summary,
            diff_detail=diff_detail,
            modification_types=[ModificationType(t) for t in analysis["modification_types"]],
            ai_reason=analysis["reason_analysis"],
            suggested_prompt_update=analysis["suggested_prompt_addition"],
            confidence=analysis["confidence"]
        )
    
    def _summarize_diff(self, original: str, modified: str) -> str:
        """產生人類可讀的差異摘要"""
        orig_len = len(original)
        mod_len = len(modified)
        
        changes = []
        if mod_len > orig_len * 1.2:
            changes.append(f"長度增加 {((mod_len/orig_len)-1)*100:.0f}%")
        elif mod_len < orig_len * 0.8:
            changes.append(f"長度減少 {(1-(mod_len/orig_len))*100:.0f}%")
        
        # 檢查 emoji 變化
        import re
        orig_emoji = len(re.findall(r'[\U0001F600-\U0001F64F]', original))
        mod_emoji = len(re.findall(r'[\U0001F600-\U0001F64F]', modified))
        if mod_emoji > orig_emoji:
            changes.append(f"增加 {mod_emoji - orig_emoji} 個表情")
        elif mod_emoji < orig_emoji:
            changes.append(f"減少 {orig_emoji - mod_emoji} 個表情")
        
        return "；".join(changes) if changes else "細微調整"

    async def _ai_analyze(self, original, modified, diff, context) -> dict:
        """呼叫 Claude 分析修改"""
        response = await claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{
                "role": "user", 
                "content": self.ANALYSIS_PROMPT.format(
                    original=original,
                    modified=modified,
                    diff=diff,
                    customer_type=context.get("customer_type", "未知"),
                    conversation_stage=context.get("stage", "未知"),
                    source=context.get("source", "未知")
                )
            }]
        )
        return json.loads(response.content[0].text)


class LearningEngine:
    """持續學習引擎"""
    
    def __init__(self, db):
        self.db = db
        self.analyzer = ModificationAnalyzer()
    
    async def record_modification(
        self,
        response_id: str,
        original: str,
        final: str,
        context: dict
    ):
        """記錄並分析一次修改"""
        
        # 1. 分析修改
        analysis = await self.analyzer.analyze(original, final, context)
        
        # 2. 存入資料庫
        modification = await self.db.modifications.insert({
            "response_id": response_id,
            "diff_summary": analysis.diff_summary,
            "diff_detail": analysis.diff_detail,
            "ai_analyzed_reason": analysis.ai_reason,
            "modification_types": [t.value for t in analysis.modification_types],
            "suggested_prompt_update": analysis.suggested_prompt_update,
            "confidence": analysis.confidence,
            "created_at": datetime.now()
        })
        
        # 3. 更新學習權重
        await self._update_learning_weights(analysis)
        
        return modification
    
    async def _update_learning_weights(self, analysis: ModificationAnalysis):
        """更新 RAG 和 Prompt 的學習權重"""
        
        # 如果這類修改頻繁出現，增加權重
        for mod_type in analysis.modification_types:
            pattern = await self.db.learning_patterns.find_one({
                "type": mod_type.value
            })
            
            if pattern:
                # 增加權重
                await self.db.learning_patterns.update(
                    {"_id": pattern["_id"]},
                    {"$inc": {"weight": 1}, "$set": {"last_seen": datetime.now()}}
                )
            else:
                # 新增模式
                await self.db.learning_patterns.insert({
                    "type": mod_type.value,
                    "weight": 1,
                    "suggested_prompt": analysis.suggested_prompt_update,
                    "first_seen": datetime.now(),
                    "last_seen": datetime.now()
                })
    
    async def get_dynamic_prompt_additions(self) -> str:
        """根據學習記錄，動態產生 prompt 補充"""
        
        # 取得高權重的學習模式
        patterns = await self.db.learning_patterns.find({
            "weight": {"$gte": 3}  # 至少出現3次
        }).sort("weight", -1).limit(10)
        
        additions = []
        for p in patterns:
            if p.get("suggested_prompt"):
                additions.append(f"- {p['suggested_prompt']}")
        
        if additions:
            return "\n## 根據過往經驗，請特別注意：\n" + "\n".join(additions)
        return ""
    
    async def get_similar_successful_responses(
        self, 
        context: dict,
        limit: int = 3
    ) -> list:
        """找出類似情境下，人類滿意的回覆（作為 few-shot 範例）"""
        
        # 找出沒有被修改、或修改很少的回覆
        successful = await self.db.responses.find({
            "is_modified": False,  # 直接採用 AI 草稿
            "context.customer_type": context.get("customer_type"),
            "context.stage": context.get("stage")
        }).limit(limit)
        
        return [r["final_content"] for r in successful]
