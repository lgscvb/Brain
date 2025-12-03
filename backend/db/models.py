"""
Brain - 資料庫模型
定義所有的 SQLAlchemy ORM 模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import ARRAY


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


class KnowledgeChunk(Base):
    """知識庫 Chunk 模型 - RAG 系統核心"""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)

    # 內容
    content = Column(Text, nullable=False)  # 知識內容

    # 分類
    category = Column(String(50), nullable=False)  # spin_question, value_prop, objection, faq, service_info
    sub_category = Column(String(100), nullable=True)  # 子分類，如 S/P/I/N, price, address 等

    # 適用場景
    service_type = Column(String(50), nullable=True)  # address_service, coworking, private_office, meeting_room

    # 元資料（注意：metadata 是 SQLAlchemy 保留字，故使用 extra_data）
    extra_data = Column(JSON, nullable=True)  # 額外資訊，如標籤、來源、優先級等

    # 向量嵌入（PostgreSQL + pgvector 使用）
    # 注意：實際向量存儲在 embedding_vector 欄位
    # 本地開發時使用 JSON 格式存儲，生產環境使用 pgvector
    embedding_json = Column(JSON, nullable=True)  # 備用：JSON 格式存儲向量（本地開發用）

    # 狀態
    is_active = Column(Boolean, default=True)  # 是否啟用

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
