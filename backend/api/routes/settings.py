"""
Brain - 設定管理 API 路由
提供環境變數的讀取與更新功能
"""
import os
from pathlib import Path
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class SettingsUpdate(BaseModel):
    """設定更新 Schema"""
    ANTHROPIC_API_KEY: Optional[str] = None
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_CHANNEL_SECRET: Optional[str] = None


class SettingsRead(BaseModel):
    """設定讀取 Schema"""
    ANTHROPIC_API_KEY: Optional[str] = None
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_CHANNEL_SECRET: Optional[str] = None
    ANTHROPIC_API_KEY_SET: bool = False
    LINE_CHANNEL_ACCESS_TOKEN_SET: bool = False
    LINE_CHANNEL_SECRET_SET: bool = False


def get_env_file_path() -> Path:
    """取得 .env 檔案路徑"""
    # 從 backend 目錄往上一層找 .env
    backend_dir = Path(__file__).parent.parent.parent
    env_path = backend_dir.parent / ".env"
    return env_path


def read_env_file() -> Dict[str, str]:
    """讀取 .env 檔案"""
    env_path = get_env_file_path()
    env_vars = {}
    
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def write_env_file(env_vars: Dict[str, str]):
    """寫入 .env 檔案"""
    env_path = get_env_file_path()
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write("# Server\n")
        f.write(f"PORT={env_vars.get('PORT', '8787')}\n")
        f.write(f"HOST={env_vars.get('HOST', '0.0.0.0')}\n")
        f.write(f"DEBUG={env_vars.get('DEBUG', 'true')}\n")
        f.write("\n# Database\n")
        f.write(f"DATABASE_URL={env_vars.get('DATABASE_URL', 'sqlite+aiosqlite:///./brain.db')}\n")
        f.write("\n# LINE\n")
        f.write(f"LINE_CHANNEL_ACCESS_TOKEN={env_vars.get('LINE_CHANNEL_ACCESS_TOKEN', '')}\n")
        f.write(f"LINE_CHANNEL_SECRET={env_vars.get('LINE_CHANNEL_SECRET', '')}\n")
        f.write("\n# Claude AI\n")
        f.write(f"ANTHROPIC_API_KEY={env_vars.get('ANTHROPIC_API_KEY', '')}\n")
        f.write("\n# Frontend\n")
        f.write(f"VITE_API_URL={env_vars.get('VITE_API_URL', 'http://localhost:8787')}\n")


@router.get("/settings", response_model=SettingsRead)
async def get_settings():
    """
    取得當前設定
    
    注意：出於安全考量，只回傳是否已設定，不回傳實際值
    """
    env_vars = read_env_file()
    
    return SettingsRead(
        ANTHROPIC_API_KEY=None,  # 不回傳實際值
        LINE_CHANNEL_ACCESS_TOKEN=None,
        LINE_CHANNEL_SECRET=None,
        ANTHROPIC_API_KEY_SET=bool(env_vars.get('ANTHROPIC_API_KEY')),
        LINE_CHANNEL_ACCESS_TOKEN_SET=bool(env_vars.get('LINE_CHANNEL_ACCESS_TOKEN')),
        LINE_CHANNEL_SECRET_SET=bool(env_vars.get('LINE_CHANNEL_SECRET'))
    )


@router.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """
    更新設定
    
    注意：更新後需要重啟伺服器才會生效
    """
    try:
        # 讀取現有設定
        env_vars = read_env_file()
        
        # 更新指定的值（只更新非 None 的值）
        if settings.ANTHROPIC_API_KEY is not None:
            env_vars['ANTHROPIC_API_KEY'] = settings.ANTHROPIC_API_KEY
        
        if settings.LINE_CHANNEL_ACCESS_TOKEN is not None:
            env_vars['LINE_CHANNEL_ACCESS_TOKEN'] = settings.LINE_CHANNEL_ACCESS_TOKEN
        
        if settings.LINE_CHANNEL_SECRET is not None:
            env_vars['LINE_CHANNEL_SECRET'] = settings.LINE_CHANNEL_SECRET
        
        # 寫入檔案
        write_env_file(env_vars)
        
        return {
            "success": True,
            "message": "設定已更新，請重啟伺服器以套用變更",
            "restart_required": True
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新設定失敗: {str(e)}")


@router.get("/settings/webhook-url")
async def get_webhook_url():
    """
    取得 LINE Webhook URL 建議
    
    返回當前伺服器的 webhook URL（如果在開發環境則提示需要使用 ngrok）
    """
    from config import settings
    
    # 檢查是否在本地開發
    is_local = settings.HOST in ["localhost", "127.0.0.1", "0.0.0.0"]
    
    if is_local:
        return {
            "webhook_url": None,
            "is_local": True,
            "message": "本地開發環境需要使用 ngrok 或類似工具來建立公開 URL",
            "instructions": [
                "1. 安裝 ngrok: https://ngrok.com/download",
                "2. 執行: ngrok http 8787",
                "3. 複製 ngrok 提供的 https URL",
                "4. 在 LINE Console 中設定: <ngrok-url>/webhook/line"
            ]
        }
    else:
        # 生產環境
        return {
            "webhook_url": f"https://<your-domain>/webhook/line",
            "is_local": False,
            "message": "請將此 URL 設定到 LINE Console 的 Webhook URL"
        }
