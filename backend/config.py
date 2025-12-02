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
    
    # Claude AI
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"  # 預設使用 Claude 3.5 Sonnet
    
    # 自動回覆模式（預設：手動審核）
    AUTO_REPLY_MODE: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全域設定實例
settings = Settings()
