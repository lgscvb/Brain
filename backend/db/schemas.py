"""
Brain - Pydantic Schemas
定義 API 請求/回應的資料結構
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ==================== Message Schemas ====================

class MessageBase(BaseModel):
    """訊息基礎 Schema"""
    source: str
    sender_id: str
    sender_name: str
    content: str
    priority: Optional[str] = "medium"


class MessageCreate(MessageBase):
    """建立訊息 Schema"""
    pass


class DraftRead(BaseModel):
    """草稿讀取 Schema"""
    id: int
    content: str
    strategy: Optional[str] = None
    intent: Optional[str] = None
    is_selected: bool
    created_at: datetime
    # 回饋欄位
    is_good: Optional[bool] = None
    rating: Optional[int] = None
    feedback_reason: Optional[str] = None
    feedback_at: Optional[datetime] = None
    auto_analysis: Optional[str] = None
    improvement_tags: Optional[List[str]] = None

    class Config:
        from_attributes = True


class DraftFeedback(BaseModel):
    """草稿回饋 Schema"""
    is_good: Optional[bool] = None           # 快速回饋：好/不好
    rating: Optional[int] = None             # 評分：1-5 星
    feedback_reason: Optional[str] = None    # 修改/不好原因


class ResponseRead(BaseModel):
    """回覆讀取 Schema"""
    id: int
    original_content: Optional[str] = None
    final_content: str
    is_modified: bool
    modification_reason: Optional[str] = None
    sent_at: datetime
    
    class Config:
        from_attributes = True


class MessageSimple(MessageBase):
    """訊息讀取 Schema（簡化版，不含草稿）"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageRead(MessageBase):
    """訊息讀取 Schema（含草稿）"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    drafts: List[DraftRead] = []
    
    class Config:
        from_attributes = True


class MessageList(BaseModel):
    """訊息列表 Schema"""
    messages: List[MessageSimple]  # 使用簡化版避免載入關聯
    total: int


# ==================== Response Schemas ====================

class ResponseCreate(BaseModel):
    """建立回覆 Schema"""
    content: str
    draft_id: Optional[int] = None


# ==================== Stats Schemas ====================

class StatsRead(BaseModel):
    """統計資料 Schema"""
    pending_count: int
    today_sent: int
    modification_rate: float
    avg_response_time: Optional[float] = None


class LearningRecord(BaseModel):
    """學習記錄 Schema"""
    original_content: str
    final_content: str
    modification_reason: Optional[str] = None
    created_at: datetime
