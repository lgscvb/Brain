"""
Brain - 配置管理
從環境變數讀取所有設定
"""
from pydantic_settings import BaseSettings
from typing import Optional


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

    # === LLM Routing 模型分流設定 ===
    # 聰明模型：處理 Router 判斷、複雜邏輯、稅務問題、SPIN 銷售
    MODEL_SMART: str = "anthropic/claude-sonnet-4.5"

    # 快速模型：處理簡單回覆、地址查詢、問候語
    # 使用 Gemini Flash，成本只有 Haiku 的 1/4
    MODEL_FAST: str = "google/gemini-flash-1.5"

    # 是否啟用 LLM Routing（模型分流）
    ENABLE_ROUTING: bool = True

    # 對話上下文設定
    CONVERSATION_HISTORY_LIMIT: int = 30  # 取得最近幾則對話作為上下文

    # Extended Thinking（延伸思考模式）- 僅限 Anthropic 直連
    ENABLE_EXTENDED_THINKING: bool = False
    THINKING_BUDGET_TOKENS: int = 10000

    # 自動回覆模式（預設：手動審核）
    AUTO_REPLY_MODE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


# 全域設定實例
settings = Settings()
