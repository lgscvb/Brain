"""
Brain - 共用型別定義

【為什麼需要型別提示】
1. 開發時 IDE 可以自動補全，減少打錯字
2. 靜態分析工具（mypy）可以在執行前找到錯誤
3. 程式碼即文件，讀程式碼的人可以知道資料結構

【TypedDict vs dataclass】
- TypedDict：適合 JSON 資料、API 回應（本質是 dict）
- dataclass：適合內部物件、有方法的類別

這裡主要用 TypedDict，因為大部分資料來自 API 或 JSON。
"""
from typing import TypedDict, Optional, List, Literal


# ============================================================
# LLM Routing 相關型別
# ============================================================

class UsageInfo(TypedDict, total=False):
    """
    API 用量資訊

    【欄位說明】
    - input_tokens: 輸入 token 數（prompt）
    - output_tokens: 輸出 token 數（completion）
    - model: 使用的模型名稱

    【total=False 的意思】
    表示這些欄位都是可選的（不一定每個 API 都回傳）
    """
    input_tokens: int
    output_tokens: int
    model: str


# 複雜度等級（Literal 確保只能是這些值）
Complexity = Literal["SIMPLE", "COMPLEX", "BOOKING", "PHOTO"]


class RoutingResult(TypedDict, total=False):
    """
    LLM Routing 判斷結果

    【欄位說明】
    - complexity: 任務複雜度
      - SIMPLE: 簡單任務（用便宜的 Fast Model）
      - COMPLEX: 複雜任務（用強大的 Smart Model）
      - BOOKING: 會議室預約（特殊處理流程）
      - PHOTO: 照片相關（需要視覺處理）
    - reason: 判斷原因（給人看的）
    - suggested_intent: 建議的意圖分類
    - _usage: API 用量（內部使用，前綴 _ 表示非公開欄位）

    【範例】
    {
        "complexity": "SIMPLE",
        "reason": "簡單問候",
        "suggested_intent": "服務諮詢",
        "_usage": {"input_tokens": 50, "output_tokens": 30, "model": "gemini-flash"}
    }
    """
    complexity: Complexity
    reason: str
    suggested_intent: str
    _usage: UsageInfo


class DraftResult(TypedDict, total=False):
    """
    草稿生成結果

    【欄位說明】
    - intent: AI 判斷的客戶意圖（如「服務諮詢」「價格詢問」）
    - strategy: 回覆策略說明（如「SPIN-S 了解現況」）
    - draft: 生成的回覆草稿（給客服審核修改）
    - next_action: 建議的下一步動作
    - _usage: API 用量

    【範例】
    {
        "intent": "價格詢問",
        "strategy": "提供價格資訊，引導進一步諮詢",
        "draft": "您好！我們的營業地址服務每月 $2,500 起...",
        "next_action": "等待客戶決定方案"
    }
    """
    intent: str
    strategy: str
    draft: str
    next_action: str
    _usage: UsageInfo


class GenerateResponseResult(TypedDict):
    """
    通用 AI 回應結果

    【用途】
    - 分析修改原因
    - 其他通用 AI 回應
    """
    content: str
    model: str
    usage: UsageInfo


# ============================================================
# 意圖分類相關型別
# ============================================================

class IntentResult(TypedDict):
    """
    意圖分類結果

    【欄位說明】
    - intent: 主要意圖（如「服務諮詢」「異議處理」）
    - sub_intent: 子意圖（更精確的分類，可能為 None）
    - matched_keywords: 匹配到的關鍵字列表
    - confidence: 信心度（0.0 ~ 1.0）

    【信心度計算】
    confidence = 匹配關鍵字數 / 節點總關鍵字數
    例如：節點有 4 個關鍵字，訊息匹配 2 個 → 0.5

    【範例】
    {
        "intent": "服務諮詢",
        "sub_intent": "價格詢問",
        "matched_keywords": ["多少錢", "費用"],
        "confidence": 0.67
    }
    """
    intent: str
    sub_intent: Optional[str]
    matched_keywords: List[str]
    confidence: float


class IntentNode(TypedDict, total=False):
    """
    意圖節點（來自 logic_tree.json）

    【結構說明】
    意圖樹是巢狀結構：
    - 根節點：主要意圖（如「服務諮詢」）
    - 子節點：子意圖（如「價格詢問」「合約條款」）

    【欄位說明】
    - name: 節點名稱
    - keywords: 觸發關鍵字列表
    - children: 子節點列表
    - spin_phase: SPIN 銷售階段（S/P/I/N）
    - spin_guidance: SPIN 話術指引
    """
    name: str
    keywords: List[str]
    children: List["IntentNode"]
    spin_phase: List[str]
    spin_guidance: str


# ============================================================
# RAG 知識檢索相關型別
# ============================================================

class SearchResult(TypedDict):
    """
    RAG 搜尋結果

    【欄位說明】
    - id: 知識塊 ID
    - content: 知識內容
    - category: 分類（如「服務說明」「常見問題」）
    - similarity: 相似度分數（0.0 ~ 1.0，越高越相關）
    - source: 來源（可選）

    【範例】
    {
        "id": 42,
        "content": "營業地址服務每月 $2,500 起...",
        "category": "價格資訊",
        "similarity": 0.89
    }
    """
    id: int
    content: str
    category: str
    similarity: float


class SearchResultWithSource(SearchResult, total=False):
    """帶來源資訊的搜尋結果"""
    source: str
    metadata: dict


class RAGSearchResult(TypedDict, total=False):
    """
    RAG 搜尋結果（完整版，用於 rag_service）

    【欄位說明】
    - id: 知識塊 ID
    - content: 知識內容
    - category: 主分類
    - sub_category: 子分類
    - service_type: 服務類型
    - metadata: 額外資料
    - similarity: 相似度分數（0.0 ~ 1.0）

    【與 SearchResult 的差異】
    SearchResult 是簡化版，RAGSearchResult 是完整版
    （多了 sub_category, service_type, metadata）
    """
    id: int
    content: str
    category: str
    sub_category: Optional[str]
    service_type: Optional[str]
    metadata: Optional[dict]
    similarity: float


# ============================================================
# CRM 客戶資料相關型別
# ============================================================

class ContractInfo(TypedDict, total=False):
    """
    合約資訊

    【欄位說明】
    - id: 合約 ID
    - project_name: 方案名稱（如「虛擬辦公室」「商務中心」）
    - contract_type: 合約類型
    - start_day: 開始日期
    - end_day: 結束日期
    - status: 狀態（active/inactive）
    - contract_status: 詳細狀態（active/expired/pending/cancelled）
    - next_pay_day: 下次繳費日
    - current_payment: 當前月租金
    """
    id: int
    project_name: str
    contract_type: str
    start_day: str
    end_day: str
    status: str
    contract_status: str
    next_pay_day: Optional[str]
    current_payment: Optional[float]


class PaymentStatus(TypedDict, total=False):
    """
    繳費狀態

    【欄位說明】
    - overdue: 是否有逾期款項
    - overdue_count: 逾期筆數
    - overdue_amount: 逾期總金額
    - upcoming: 是否有即將到期的款項
    - upcoming_date: 即將到期日期
    - upcoming_amount: 即將到期金額
    """
    overdue: bool
    overdue_count: int
    overdue_amount: float
    upcoming: bool
    upcoming_date: str
    upcoming_amount: float


class CustomerData(TypedDict, total=False):
    """
    CRM 客戶資料

    【欄位說明】
    - id: 客戶 ID
    - name: 客戶姓名
    - phone: 電話
    - email: Email
    - company_name: 公司名稱
    - line_id: LINE 用戶 ID
    - contracts: 合約列表
    - payment_status: 繳費狀態
    - created_at: 建立時間
    """
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str]
    company_name: Optional[str]
    line_id: str
    contracts: List[ContractInfo]
    payment_status: PaymentStatus
    created_at: str


class PaymentRecord(TypedDict, total=False):
    """
    繳費記錄

    【欄位說明】
    - id: 記錄 ID
    - pay_day: 繳費日期
    - pay_type: 繳費類型（月租/押金/...）
    - amount: 金額
    - status: 狀態（paid/pending/overdue）
    - payment_method: 付款方式
    """
    id: int
    pay_day: str
    pay_type: str
    amount: float
    status: str
    payment_method: Optional[str]


# ============================================================
# API 用量統計相關型別
# ============================================================

class UsageStats(TypedDict):
    """
    API 用量統計

    【欄位說明】
    - input_tokens: 總輸入 token 數
    - output_tokens: 總輸出 token 數
    - total_tokens: 總 token 數
    - estimated_cost_usd: 預估費用（美元）
    - api_calls: API 呼叫次數
    - errors: 錯誤次數
    """
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    api_calls: int
    errors: int


class DailyStats(TypedDict):
    """每日統計"""
    date: str
    tokens: int
    cost: float
    calls: int


class OperationStats(TypedDict):
    """操作類型統計"""
    operation: str
    tokens: int
    cost: float
    calls: int


class UsageStatsResponse(TypedDict):
    """
    /usage/stats API 回應

    【結構說明】
    - period_days: 統計期間天數
    - total: 總計統計
    - today: 今日統計
    - daily: 每日明細
    - by_operation: 按操作類型統計
    """
    period_days: int
    total: UsageStats
    today: UsageStats
    daily: List[DailyStats]
    by_operation: List[OperationStats]


# ============================================================
# 會議室預約相關型別
# ============================================================

class TimeSlot(TypedDict):
    """時段"""
    start: str
    end: str


class BookingInfo(TypedDict, total=False):
    """
    會議室預約資訊

    【欄位說明】
    - id: 預約 ID
    - room_id: 會議室 ID
    - room_name: 會議室名稱
    - customer_line_id: 客戶 LINE ID
    - booking_date: 預約日期
    - time_slot: 時段
    - status: 狀態（pending/confirmed/cancelled/completed）
    - notes: 備註
    """
    id: int
    room_id: int
    room_name: str
    customer_line_id: str
    booking_date: str
    time_slot: TimeSlot
    status: str
    notes: Optional[str]


class BookingRecord(TypedDict):
    """
    預約記錄（用於 _show_my_bookings）

    【欄位說明】
    - id: 預約 ID
    - booking_number: 預約編號
    - date: 預約日期
    - start_time: 開始時間
    - end_time: 結束時間
    - status: 狀態
    """
    id: int
    booking_number: str
    date: str
    start_time: str
    end_time: str
    status: str


# 預約意圖類型
BookingIntentType = Literal["book", "query", "cancel", None]


class CancelResult(TypedDict, total=False):
    """取消預約結果"""
    success: bool
    error: str


# ============================================================
# 學習引擎相關型別
# ============================================================

class ModificationRecord(TypedDict, total=False):
    """
    修改記錄

    【欄位說明】
    - id: 記錄 ID
    - original_content: 原始 AI 草稿
    - final_content: 人工修改後的內容
    - modification_reason: 修改原因分析
    - sent_at: 發送時間
    """
    id: int
    original_content: str
    final_content: str
    modification_reason: Optional[str]
    sent_at: str


# ============================================================
# Prompt 版本管理相關型別
# ============================================================

class PromptVersionInfo(TypedDict, total=False):
    """
    Prompt 版本資訊

    【欄位說明】
    - id: 版本記錄 ID
    - prompt_key: Prompt 識別鍵（如「draft_prompt」「router_prompt」）
    - version: 版本號
    - content: Prompt 內容
    - description: 版本說明
    - is_active: 是否為活躍版本
    - created_by: 建立者
    - created_at: 建立時間
    """
    id: int
    prompt_key: str
    version: int
    content: str
    description: Optional[str]
    is_active: bool
    created_by: str
    created_at: str


class PromptSummary(TypedDict):
    """
    Prompt 摘要（用於列表顯示）

    【欄位說明】
    - prompt_key: Prompt 識別鍵
    - active_version: 當前活躍版本號
    - total_versions: 總版本數
    - last_updated: 最後更新時間
    """
    prompt_key: str
    active_version: Optional[int]
    total_versions: int
    last_updated: Optional[str]
