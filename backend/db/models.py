"""
Brain - 資料庫模型
定義所有的 SQLAlchemy ORM 模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
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
