"""
Brain - FastAPI 主程式
啟動點：uvicorn main:app --reload --port 8787
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db.database import create_tables

# 初始化日誌系統
from logger import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # Startup
    logger.info("🚀 Brain 正在啟動...")
    print("🚀 Brain 正在啟動...")
    await create_tables()
    logger.info("✅ 資料庫已初始化")
    print("✅ 資料庫已初始化")
    yield
    # Shutdown
    logger.info("👋 Brain 正在關閉...")
    print("👋 Brain 正在關閉...")


# 建立 FastAPI 應用
app = FastAPI(
    title="Brain - Hour Jungle AI 輔助客服系統",
    description="""
    ## 功能特色
    
    - 🤖 **AI 智能回覆**：整合 Claude 3.5 Sonnet，基於 SPIN 銷售框架
    - 💬 **雙模式運行**：手動審核 / 自動回覆靈活切換
    - 📊 **完整管理**：訊息管理、系統日誌、統計分析
    - 🔗 **LINE 整合**：支援 LINE Official Account Webhook
    
    ## 技術棧
    
    - **框架**：FastAPI + SQLAlchemy (async)
    - **AI**：Anthropic Claude 3.5 Sonnet
    - **資料庫**：SQLite
    - **部署**：Docker + GCP + Cloudflare
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "Hour Jungle Team",
        "url": "https://brain.yourspce.org",
    },
    license_info={
        "name": "MIT License",
    },
)

# CORS 設定（允許前端連接）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 預設開發伺服器
        "http://localhost:3000",  # 備用前端 port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 路由註冊 ====================
from api.routes import messages, webhooks, stats, settings, logs, health

app.include_router(health.router, prefix="/api", tags=["健康檢查 & 系統狀態"])
app.include_router(messages.router, prefix="/api", tags=["訊息管理"])
app.include_router(webhooks.router, tags=["Webhook 接收"])
app.include_router(stats.router, prefix="/api", tags=["統計資料"])
app.include_router(settings.router, prefix="/api", tags=["系統設定"])
app.include_router(logs.router, prefix="/api", tags=["日誌管理"])



@app.get(
    "/",
    summary="API 根端點",
    description="返回 API 基本資訊和狀態",
    response_description="API 基本資訊"
)
async def root():
    """
    API 根端點
    
    返回系統名稱、版本和運行狀態。
    """
    return {
        "name": "Brain API",
        "version": "1.0.0",
        "status": "running",
        "message": "Hour Jungle AI 輔助客服系統",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
