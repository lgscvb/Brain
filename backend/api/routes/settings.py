"""
Brain - 設定管理 API 路由
提供環境變數的讀取與更新功能
支援 OpenRouter + LLM Routing 設定
"""
import os
from pathlib import Path
from typing import Dict, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()


class SettingsUpdate(BaseModel):
    """設定更新 Schema"""
    # AI Provider
    AI_PROVIDER: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # LLM Routing
    ENABLE_ROUTING: Optional[bool] = None
    MODEL_SMART: Optional[str] = None
    MODEL_FAST: Optional[str] = None

    # Anthropic 直連
    CLAUDE_MODEL: Optional[str] = None
    ENABLE_EXTENDED_THINKING: Optional[bool] = None
    THINKING_BUDGET_TOKENS: Optional[int] = None

    # LINE
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_CHANNEL_SECRET: Optional[str] = None

    # System
    AUTO_REPLY_MODE: Optional[bool] = None


class SettingsRead(BaseModel):
    """設定讀取 Schema"""
    # AI Provider
    AI_PROVIDER: str = "openrouter"
    OPENROUTER_API_KEY_SET: bool = False
    ANTHROPIC_API_KEY_SET: bool = False

    # LLM Routing
    ENABLE_ROUTING: bool = True
    MODEL_SMART: str = "anthropic/claude-sonnet-4.5"
    MODEL_FAST: str = "google/gemini-flash-1.5"

    # Anthropic 直連
    CLAUDE_MODEL: str = "claude-sonnet-4-5"
    ENABLE_EXTENDED_THINKING: bool = False
    THINKING_BUDGET_TOKENS: int = 10000

    # LINE
    LINE_CHANNEL_ACCESS_TOKEN_SET: bool = False
    LINE_CHANNEL_SECRET_SET: bool = False

    # System
    AUTO_REPLY_MODE: bool = False


class ModelOption(BaseModel):
    """模型選項"""
    id: str
    name: str
    provider: str
    cost: str
    recommended: bool = False


# 可用的模型選項
AVAILABLE_MODELS = {
    "smart": [
        {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "provider": "OpenRouter", "cost": "$3/$15 per MTok", "recommended": True},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet (舊版)", "provider": "OpenRouter", "cost": "$3/$15 per MTok"},
        {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "provider": "OpenRouter", "cost": "$15/$75 per MTok"},
        {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "OpenRouter", "cost": "$10/$30 per MTok"},
    ],
    "fast": [
        {"id": "google/gemini-flash-1.5", "name": "Gemini 1.5 Flash", "provider": "OpenRouter", "cost": "$0.075/$0.30 per MTok", "recommended": True},
        {"id": "google/gemini-flash-1.5-8b", "name": "Gemini 1.5 Flash 8B", "provider": "OpenRouter", "cost": "$0.0375/$0.15 per MTok"},
        {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku", "provider": "OpenRouter", "cost": "$0.25/$1.25 per MTok"},
        {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "provider": "OpenRouter", "cost": "$0.05/$0.05 per MTok"},
        {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "provider": "OpenRouter", "cost": "$0.14/$0.28 per MTok"},
    ],
    "anthropic_direct": [
        {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5.5", "provider": "Anthropic", "cost": "$3/$15 per MTok", "recommended": True},
        {"id": "claude-opus-4-5", "name": "Claude Opus 4.5", "provider": "Anthropic", "cost": "$15/$75 per MTok"},
        {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5", "provider": "Anthropic", "cost": "$1/$5 per MTok"},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (舊版)", "provider": "Anthropic", "cost": "$3/$15 per MTok"},
    ]
}


def get_env_file_path() -> Path:
    """取得 .env 檔案路徑"""
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
        f.write(f"PORT={env_vars.get('PORT', '8000')}\n")
        f.write(f"HOST={env_vars.get('HOST', '0.0.0.0')}\n")
        f.write(f"DEBUG={env_vars.get('DEBUG', 'false')}\n")

        f.write("\n# Database\n")
        f.write(f"DATABASE_URL={env_vars.get('DATABASE_URL', 'sqlite+aiosqlite:///./data/brain.db')}\n")

        f.write("\n# LINE\n")
        f.write(f"LINE_CHANNEL_ACCESS_TOKEN={env_vars.get('LINE_CHANNEL_ACCESS_TOKEN', '')}\n")
        f.write(f"LINE_CHANNEL_SECRET={env_vars.get('LINE_CHANNEL_SECRET', '')}\n")

        f.write("\n# AI Provider\n")
        f.write(f"AI_PROVIDER={env_vars.get('AI_PROVIDER', 'openrouter')}\n")

        f.write("\n# OpenRouter\n")
        f.write(f"OPENROUTER_API_KEY={env_vars.get('OPENROUTER_API_KEY', '')}\n")

        f.write("\n# LLM Routing\n")
        f.write(f"ENABLE_ROUTING={env_vars.get('ENABLE_ROUTING', 'true')}\n")
        f.write(f"MODEL_SMART={env_vars.get('MODEL_SMART', 'anthropic/claude-3.5-sonnet')}\n")
        f.write(f"MODEL_FAST={env_vars.get('MODEL_FAST', 'google/gemini-flash-1.5')}\n")

        f.write("\n# Anthropic Direct\n")
        f.write(f"ANTHROPIC_API_KEY={env_vars.get('ANTHROPIC_API_KEY', '')}\n")
        f.write(f"CLAUDE_MODEL={env_vars.get('CLAUDE_MODEL', 'claude-sonnet-4-5')}\n")
        f.write(f"ENABLE_EXTENDED_THINKING={env_vars.get('ENABLE_EXTENDED_THINKING', 'false')}\n")
        f.write(f"THINKING_BUDGET_TOKENS={env_vars.get('THINKING_BUDGET_TOKENS', '10000')}\n")

        f.write("\n# System\n")
        f.write(f"AUTO_REPLY_MODE={env_vars.get('AUTO_REPLY_MODE', 'false')}\n")

        f.write("\n# Frontend\n")
        f.write(f"VITE_API_URL={env_vars.get('VITE_API_URL', 'http://localhost:8000')}\n")


@router.get("/settings", response_model=SettingsRead)
async def get_settings():
    """
    取得當前設定

    注意：出於安全考量，API Key 只回傳是否已設定，不回傳實際值
    """
    env_vars = read_env_file()

    return SettingsRead(
        # AI Provider
        AI_PROVIDER=env_vars.get('AI_PROVIDER', 'openrouter'),
        OPENROUTER_API_KEY_SET=bool(env_vars.get('OPENROUTER_API_KEY')),
        ANTHROPIC_API_KEY_SET=bool(env_vars.get('ANTHROPIC_API_KEY')),

        # LLM Routing
        ENABLE_ROUTING=env_vars.get('ENABLE_ROUTING', 'true').lower() == 'true',
        MODEL_SMART=env_vars.get('MODEL_SMART', 'anthropic/claude-3.5-sonnet'),
        MODEL_FAST=env_vars.get('MODEL_FAST', 'google/gemini-flash-1.5'),

        # Anthropic 直連
        CLAUDE_MODEL=env_vars.get('CLAUDE_MODEL', 'claude-sonnet-4-5'),
        ENABLE_EXTENDED_THINKING=env_vars.get('ENABLE_EXTENDED_THINKING', 'false').lower() == 'true',
        THINKING_BUDGET_TOKENS=int(env_vars.get('THINKING_BUDGET_TOKENS', '10000')),

        # LINE
        LINE_CHANNEL_ACCESS_TOKEN_SET=bool(env_vars.get('LINE_CHANNEL_ACCESS_TOKEN')),
        LINE_CHANNEL_SECRET_SET=bool(env_vars.get('LINE_CHANNEL_SECRET')),

        # System
        AUTO_REPLY_MODE=env_vars.get('AUTO_REPLY_MODE', 'false').lower() == 'true'
    )


@router.get("/settings/models")
async def get_available_models():
    """取得可用的模型列表"""
    return AVAILABLE_MODELS


@router.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """
    更新設定

    注意：更新後需要重啟伺服器才會生效
    """
    try:
        env_vars = read_env_file()

        # AI Provider
        if settings.AI_PROVIDER is not None:
            env_vars['AI_PROVIDER'] = settings.AI_PROVIDER

        if settings.OPENROUTER_API_KEY is not None:
            env_vars['OPENROUTER_API_KEY'] = settings.OPENROUTER_API_KEY

        if settings.ANTHROPIC_API_KEY is not None:
            env_vars['ANTHROPIC_API_KEY'] = settings.ANTHROPIC_API_KEY

        # LLM Routing
        if settings.ENABLE_ROUTING is not None:
            env_vars['ENABLE_ROUTING'] = 'true' if settings.ENABLE_ROUTING else 'false'

        if settings.MODEL_SMART is not None:
            env_vars['MODEL_SMART'] = settings.MODEL_SMART

        if settings.MODEL_FAST is not None:
            env_vars['MODEL_FAST'] = settings.MODEL_FAST

        # Anthropic 直連
        if settings.CLAUDE_MODEL is not None:
            env_vars['CLAUDE_MODEL'] = settings.CLAUDE_MODEL

        if settings.ENABLE_EXTENDED_THINKING is not None:
            env_vars['ENABLE_EXTENDED_THINKING'] = 'true' if settings.ENABLE_EXTENDED_THINKING else 'false'

        if settings.THINKING_BUDGET_TOKENS is not None:
            env_vars['THINKING_BUDGET_TOKENS'] = str(settings.THINKING_BUDGET_TOKENS)

        # LINE
        if settings.LINE_CHANNEL_ACCESS_TOKEN is not None:
            env_vars['LINE_CHANNEL_ACCESS_TOKEN'] = settings.LINE_CHANNEL_ACCESS_TOKEN

        if settings.LINE_CHANNEL_SECRET is not None:
            env_vars['LINE_CHANNEL_SECRET'] = settings.LINE_CHANNEL_SECRET

        # System
        if settings.AUTO_REPLY_MODE is not None:
            env_vars['AUTO_REPLY_MODE'] = 'true' if settings.AUTO_REPLY_MODE else 'false'

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
    """取得 LINE Webhook URL 建議"""
    from config import settings

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
        return {
            "webhook_url": f"https://<your-domain>/webhook/line",
            "is_local": False,
            "message": "請將此 URL 設定到 LINE Console 的 Webhook URL"
        }
