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
    attachments = relationship("Attachment", back_populates="message", cascade="all, delete-orphan")


class Attachment(Base):
    """
    媒體附件模型

    【用途】
    儲存客戶透過 LINE 傳送的圖片、PDF 等媒體檔案：
    1. 從 LINE 下載媒體內容
    2. 上傳到 Cloudflare R2 永久存儲
    3. 使用 Claude Vision 做 OCR 提取文字
    4. OCR 結果加入對話上下文，讓 AI 理解圖片/文件內容

    【流程】
    LINE 圖片 → download_media() → R2 上傳 → Claude Vision OCR → 存入 ocr_text
    """
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)

    # LINE 訊息資訊
    line_message_id = Column(String(50), unique=True, nullable=False)  # LINE 媒體訊息 ID

    # 媒體類型
    media_type = Column(String(20), nullable=False)  # image, pdf, file, video, audio
    mime_type = Column(String(100), nullable=True)   # image/jpeg, application/pdf, etc.
    file_name = Column(String(255), nullable=True)   # 原始檔名（PDF/file 才有）
    file_size = Column(Integer, nullable=True)       # 檔案大小（bytes）

    # R2 存儲
    r2_path = Column(String(500), nullable=True)     # R2 上的路徑
    r2_url = Column(String(1000), nullable=True)     # 簽名 URL（定期更新）
    r2_url_expires_at = Column(DateTime, nullable=True)  # URL 過期時間

    # OCR 結果
    ocr_text = Column(Text, nullable=True)           # OCR 提取的文字
    ocr_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    ocr_error = Column(Text, nullable=True)          # OCR 失敗原因

    # 處理狀態
    download_status = Column(String(20), default="pending")  # pending, downloaded, failed

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)   # OCR 完成時間

    # Relationships
    message = relationship("Message", back_populates="attachments")


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
    refinements = relationship("DraftRefinement", back_populates="draft", cascade="all, delete-orphan")


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


class DraftRefinement(Base):
    """草稿修正對話模型 - 多輪修正歷史"""
    __tablename__ = "draft_refinements"

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("drafts.id"), nullable=False)
    round_number = Column(Integer, default=1)  # 第幾輪修正
    instruction = Column(Text, nullable=False)  # 用戶修正指令
    original_content = Column(Text, nullable=False)  # 修正前內容
    refined_content = Column(Text, nullable=False)  # 修正後內容
    model_used = Column(String(100), nullable=True)  # 使用的模型
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    is_accepted = Column(Boolean, nullable=True)  # 用戶是否接受此修正
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    draft = relationship("Draft", back_populates="refinements")


class TrainingExport(Base):
    """訓練資料匯出記錄"""
    __tablename__ = "training_exports"

    id = Column(Integer, primary_key=True, index=True)
    export_type = Column(String(20), nullable=False)  # sft, rlhf, dpo
    record_count = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MeetingRoom(Base):
    """會議室模型"""
    __tablename__ = "meeting_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # 會議室名稱
    capacity = Column(Integer, default=6)  # 座位數
    hourly_rate = Column(Integer, default=0)  # 每小時費率（分）- 目前免費給現有客戶
    amenities = Column(JSON, default=list)  # 設備: ["投影機", "白板"]
    google_calendar_id = Column(String(255), nullable=True)  # Google Calendar ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    bookings = relationship("MeetingRoomBooking", back_populates="room", cascade="all, delete-orphan")


class MeetingRoomBooking(Base):
    """會議室預約模型"""
    __tablename__ = "meeting_room_bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_number = Column(String(30), unique=True, nullable=False)  # MR-20241215-0001
    meeting_room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)

    # 客戶資訊（來自 LINE）
    customer_line_id = Column(String(255), nullable=False)  # LINE User ID
    customer_name = Column(String(255), nullable=False)

    # 預約時間
    booking_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)  # HH:MM
    duration_minutes = Column(Integer, nullable=False)

    # Google Calendar
    google_event_id = Column(String(255), nullable=True)

    # 狀態
    status = Column(String(20), default="confirmed")  # confirmed, cancelled, completed
    cancelled_at = Column(DateTime, nullable=True)
    cancel_reason = Column(String(255), nullable=True)

    # 提醒
    reminder_sent = Column(Boolean, default=False)

    # 備註
    purpose = Column(String(255), nullable=True)  # 會議目的
    attendees_count = Column(Integer, nullable=True)  # 預計人數
    notes = Column(Text, nullable=True)
    created_by = Column(String(50), default="line")  # line, admin

    # 時間戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    room = relationship("MeetingRoom", back_populates="bookings")


class PromptVersion(Base):
    """
    Prompt 版本模型

    【用途】
    管理 AI Prompt 的版本歷史，支援：
    1. 版本追蹤：記錄每次 prompt 修改
    2. 快速回滾：新版本效果不好可以切回舊版
    3. A/B 測試：準備多個版本快速切換

    【唯一約束】
    同一個 prompt_key 的版本號不能重複
    例如：draft_prompt 只能有一個 v1, v2, v3...

    【活躍版本規則】
    每個 prompt_key 同時間只能有一個 is_active=True
    啟用新版本時會自動將舊版本設為 is_active=False
    """
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_key = Column(String(50), nullable=False, index=True)  # draft_prompt, router_prompt, etc.
    version = Column(Integer, nullable=False)  # 版本號，從 1 開始
    content = Column(Text, nullable=False)  # Prompt 內容
    description = Column(String(500), nullable=True)  # 版本說明
    is_active = Column(Boolean, default=False)  # 是否為當前使用版本
    created_by = Column(String(100), default="system")  # 建立者
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# 意圖樹模型（知識庫 DB 化）
# ============================================================

class IntentNode(Base):
    """
    意圖節點模型

    【用途】
    將 logic_tree.json 的樹狀結構存入資料庫，實現：
    1. 動態更新：不需重新部署即可調整意圖樹
    2. 版本追蹤：記錄每次修改
    3. A/B 測試：可以有多個意圖樹版本

    【樹狀結構】
    - parent_id 指向父節點，形成樹狀結構
    - parent_id = NULL 的節點是根節點（如「服務諮詢」「異議處理」）
    """
    __tablename__ = "intent_nodes"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("intent_nodes.id", ondelete="CASCADE"), nullable=True)
    node_key = Column(String(100), unique=True, nullable=False)  # 唯一識別碼，對應 JSON 的 id
    name = Column(String(200), nullable=False)  # 節點名稱
    keywords = Column(JSON, default=list)  # 觸發關鍵字列表
    spin_phases = Column(JSON, default=list)  # 適用的 SPIN 階段，如 ["S", "P"]
    spin_guidance = Column(Text, nullable=True)  # SPIN 指引說明
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)  # 排序順序
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("IntentNode", remote_side=[id], backref="children")
    spin_questions = relationship("SpinQuestion", back_populates="intent_node", cascade="all, delete-orphan")


class SpinQuestion(Base):
    """
    SPIN 問題模型

    【用途】
    儲存每個意圖節點對應的 SPIN 問題，例如：
    - S（Situation）：「您目前公司登記在哪裡？」
    - P（Problem）：「現在的地址有遇到什麼困擾嗎？」
    - I（Implication）：「如果被認定不合規，可能面臨什麼後果？」
    - N（Need-payoff）：「如果每天只要 60 元就能有金融商圈地址，有幫助嗎？」

    【service_type】
    可選欄位，用於針對特定服務類型的問題
    例如：address_service（營業地址）、coworking（共享辦公）
    """
    __tablename__ = "spin_questions"

    id = Column(Integer, primary_key=True, index=True)
    intent_node_id = Column(Integer, ForeignKey("intent_nodes.id", ondelete="CASCADE"), nullable=False)
    phase = Column(String(1), nullable=False)  # S, P, I, N
    question = Column(Text, nullable=False)
    service_type = Column(String(50), nullable=True)  # 可選：針對特定服務類型
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    intent_node = relationship("IntentNode", back_populates="spin_questions")


class SpinFramework(Base):
    """
    SPIN 框架設定模型

    【用途】
    儲存 SPIN 銷售框架的基本定義：
    - S: Situation（現況了解）
    - P: Problem（痛點挖掘）
    - I: Implication（影響放大）
    - N: Need-payoff（解決導向）
    """
    __tablename__ = "spin_framework"

    id = Column(Integer, primary_key=True, index=True)
    phase = Column(String(1), unique=True, nullable=False)  # S, P, I, N
    name = Column(String(50), nullable=False)  # Situation, Problem, etc.
    name_zh = Column(String(50), nullable=False)  # 現況了解, 痛點挖掘, etc.
    purpose = Column(Text, nullable=False)  # 此階段的目的
    signals_to_advance = Column(JSON, default=list)  # 進入下一階段的信號
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


class SpinTransitionRule(Base):
    """
    SPIN 階段轉換規則模型

    【用途】
    定義 SPIN 階段之間的轉換邏輯：
    - from_phase: 起始階段（可以是 "any" 表示任何階段）
    - to_phase: 目標階段
    - condition: 觸發條件描述
    - trigger_keywords: 觸發關鍵字

    【範例】
    S → P：客戶已提供公司型態、業務類型
    P → I：客戶承認有困擾、表達不滿
    any → N：客戶主動表達強烈興趣
    """
    __tablename__ = "spin_transition_rules"

    id = Column(Integer, primary_key=True, index=True)
    from_phase = Column(String(10), nullable=False)  # S, P, I, N, or "any"
    to_phase = Column(String(1), nullable=False)  # S, P, I, N
    condition = Column(Text, nullable=False)  # 觸發條件描述
    trigger_keywords = Column(JSON, default=list)  # 觸發關鍵字列表
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
