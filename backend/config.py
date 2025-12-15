"""
Brain - 配置管理
從環境變數讀取所有設定
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


def find_env_file() -> str:
    """尋找 .env 檔案，優先順序：當前目錄 > 父目錄"""
    current_dir = Path(__file__).parent

    # 檢查當前目錄（backend/）
    if (current_dir / ".env").exists():
        return str(current_dir / ".env")

    # 檢查父目錄（brain/）
    parent_env = current_dir.parent / ".env"
    if parent_env.exists():
        return str(parent_env)

    # 預設返回當前目錄
    return ".env"


class Settings(BaseSettings):
    """應用程式設定"""

    # Server
    PORT: int = 8787
    HOST: str = "0.0.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./brain.db"

    # LINE
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_CHANNEL_SECRET: Optional[str] = None

    # === AI Provider 設定 ===
    # 選擇使用哪個 Provider: "anthropic" 或 "openrouter"
    AI_PROVIDER: str = "openrouter"

    # Anthropic 直連（備用）
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-5"

    # OpenRouter 設定（推薦）
    OPENROUTER_API_KEY: Optional[str] = None

    # OpenAI 設定（用於 Embedding）
    OPENAI_API_KEY: Optional[str] = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # 1536 維，$0.02/1M tokens

    # === LLM Routing 模型分流設定 ===
    # 聰明模型：處理 Router 判斷、複雜邏輯、稅務問題、SPIN 銷售
    MODEL_SMART: str = "anthropic/claude-sonnet-4.5"

    # 快速模型：處理簡單回覆、地址查詢、問候語
    # 使用 Gemini 2.0 Flash，成本低且速度快
    MODEL_FAST: str = "google/gemini-2.0-flash-001"

    # 是否啟用 LLM Routing（模型分流）
    ENABLE_ROUTING: bool = True

    # 對話上下文設定
    CONVERSATION_HISTORY_LIMIT: int = 30  # 取得最近幾則對話作為上下文

    # Extended Thinking（延伸思考模式）- 僅限 Anthropic 直連
    ENABLE_EXTENDED_THINKING: bool = False
    THINKING_BUDGET_TOKENS: int = 10000

    # 自動回覆模式（預設：手動審核）
    AUTO_REPLY_MODE: bool = False

    # === 管理員密碼 ===
    # 用於保護設定頁面，防止未授權存取
    ADMIN_PASSWORD: str = "brain2024"  # 預設密碼，請在 .env 中修改

    # === 防洗頻設定 ===
    # 啟用速率限制
    ENABLE_RATE_LIMIT: bool = True

    # 時間窗口（秒）：在此時間內計算訊息數量
    RATE_LIMIT_WINDOW: int = 60

    # 最大訊息數：時間窗口內允許的最大訊息數
    RATE_LIMIT_MAX_MESSAGES: int = 10

    # 最大重複數：時間窗口內允許的相同內容最大次數
    RATE_LIMIT_MAX_DUPLICATES: int = 3

    # 冷卻時間（秒）：超過限制後的基礎冷卻時間（會隨違規次數倍增）
    RATE_LIMIT_COOLDOWN: int = 60

    # === Hour Jungle CRM 整合設定 ===
    # CRM API 基礎 URL（新版 PostgreSQL + PostgREST）
    CRM_API_URL: Optional[str] = None  # 例如: https://auto.yourspce.org

    # 舊版 API URL（向後相容）
    JUNGLE_API_URL: Optional[str] = None  # 已棄用，請使用 CRM_API_URL

    # Jungle API 金鑰（舊版用，新版不需要）
    JUNGLE_API_KEY: Optional[str] = None

    # 是否啟用 CRM 整合（查詢客戶資料）
    ENABLE_JUNGLE_INTEGRATION: bool = False

    # === Google Calendar 設定 ===
    GOOGLE_CALENDAR_CREDENTIALS: Optional[str] = None  # Service Account JSON 路徑

    class Config:
        env_file = find_env_file()
        case_sensitive = True
        extra = "ignore"  # 忽略 .env 中未定義的變數（如 VITE_API_URL）


# 全域設定實例
settings = Settings()
