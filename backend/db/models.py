"""
Brain - 資料庫模型
定義所有的 SQLAlchemy ORM 模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy Base"""
    pass


class Message(Base):
    """訊息模型"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)  # line_oa, email, phone, manual
    sender_id = Column(String(255), nullable=False)
    sender_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, drafted, sent, archived
    priority = Column(String(20), default="medium")  # high, medium, low
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drafts = relationship("Draft", back_populates="message", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="message", cascade="all, delete-orphan")


class Draft(Base):
    """AI 草稿模型"""
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    content = Column(Text, nullable=False)
    strategy = Column(Text)  # AI 策略說明
    intent = Column(String(100))  # 意圖分類
    is_selected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 人工回饋欄位（AI 自我進化系統）
    is_good = Column(Boolean, nullable=True)          # 快速回饋：👍 好 / 👎 不好
    rating = Column(Integer, nullable=True)           # 評分：1-5 星
    feedback_reason = Column(Text, nullable=True)     # 人工填寫的修改/不好原因
    feedback_at = Column(DateTime, nullable=True)     # 回饋時間

    # AI 自動分析結果
    auto_analysis = Column(Text, nullable=True)       # AI 分析修改原因
    improvement_tags = Column(JSON, nullable=True)    # 改進標籤 ["語氣", "專業度", "清晰度"]

    # Relationships
    message = relationship("Message", back_populates="drafts")


class Response(Base):
    """回覆記錄模型"""
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    draft_id = Column(Integer, ForeignKey("drafts.id"), nullable=True)
    original_content = Column(Text)  # AI 原始草稿
    final_content = Column(Text, nullable=False)  # 實際發送內容
    is_modified = Column(Boolean, default=False)
    modification_reason = Column(Text)  # AI 分析的修改原因
    sent_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    message = relationship("Message", back_populates="responses")


class APIUsage(Base):
    """API 用量追蹤模型"""
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)  # anthropic, openai, etc.
    model = Column(String(100), nullable=False)  # claude-3-5-sonnet, etc.
    operation = Column(String(100), nullable=False)  # draft_generation, analysis, etc.
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Integer, default=0)  # 儲存為分（美分），避免浮點數問題
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
