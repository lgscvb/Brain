"""
Brain - 健康檢查與系統狀態 API
提供系統健康狀態、版本資訊和依賴服務檢查
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from db.database import engine
from config import settings
import httpx
import time
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    系統健康檢查
    
    檢查項目：
    - API 服務狀態
    - 資料庫連線
    - Claude AI 連線
    - LINE API 連線
    
    Returns:
        dict: 系統健康狀態詳細資訊
    """
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    # 1. 資料庫檢查
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "up",
            "message": "資料庫連線正常"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "down",
            "message": f"資料庫連線失敗: {str(e)}"
        }
    
    # 2. Claude AI 檢查
    if settings.ANTHROPIC_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": settings.ANTHROPIC_API_KEY},
                    timeout=5.0
                )
                # API Key 有效會返回 400 (缺少必要參數) 而非 401
                if response.status_code in [400, 200]:
                    health_status["checks"]["claude_ai"] = {
                        "status": "up",
                        "message": "Claude API 連線正常"
                    }
                else:
                    health_status["checks"]["claude_ai"] = {
                        "status": "down",
                        "message": "Claude API Key 可能無效"
                    }
        except Exception as e:
            health_status["checks"]["claude_ai"] = {
                "status": "down",
                "message": f"Claude API 連線失敗: {str(e)}"
            }
    else:
        health_status["checks"]["claude_ai"] = {
            "status": "not_configured",
            "message": "Claude API Key 未設定"
        }
    
    # 3. LINE API 檢查
    if settings.LINE_CHANNEL_ACCESS_TOKEN:
        health_status["checks"]["line_api"] = {
            "status": "configured",
            "message": "LINE Access Token 已設定"
        }
    else:
        health_status["checks"]["line_api"] = {
            "status": "not_configured",
            "message": "LINE Access Token 未設定"
        }
    
    # 計算回應時間
    response_time = round((time.time() - start_time) * 1000, 2)
    health_status["response_time_ms"] = response_time
    
    return health_status


@router.get("/health/simple")
async def simple_health_check():
    """
    簡易健康檢查（適合監控系統使用）
    
    Returns:
        dict: 簡單的 OK/ERROR 狀態
    """
    try:
        # 只檢查資料庫
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "OK"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service Unavailable: {str(e)}")


@router.get("/version")
async def get_version():
    """
    取得系統版本資訊
    
    Returns:
        dict: 版本號、環境、部署資訊
    """
    return {
        "version": "1.0.0",
        "name": "Brain AI 客服系統",
        "description": "Hour Jungle AI 輔助客服系統",
        "environment": "production" if not settings.DEBUG else "development",
        "python_version": "3.11",
        "framework": "FastAPI",
        "ai_model": "Claude 3.5 Sonnet",
        "deployment": {
            "platform": "GCP Compute Engine",
            "containerized": True,
            "web_server": "Nginx"
        }
    }
