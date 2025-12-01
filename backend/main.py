"""
Brain - FastAPI 主程式
啟動點：uvicorn main:app --reload --port 8787
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # Startup
    print("🚀 Brain 正在啟動...")
    await create_tables()
    print("✅ 資料庫已初始化")
    yield
    # Shutdown
    print("👋 Brain 正在關閉...")


# 建立 FastAPI 應用
app = FastAPI(
    title="Brain - Hour Jungle AI 輔助客服系統",
    description="統一收集多管道訊息，AI 自動產生回覆草稿，人工審核後發送",
    version="0.1.0",
    lifespan=lifespan,
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
from api.routes import messages, webhooks, stats

app.include_router(messages.router, prefix="/api", tags=["messages"])
app.include_router(webhooks.router, tags=["webhooks"])
app.include_router(stats.router, prefix="/api", tags=["stats"])



@app.get("/")
async def root():
    """根端點 - 健康檢查"""
    return {
        "name": "Brain API",
        "version": "0.1.0",
        "status": "running",
        "message": "Hour Jungle AI 輔助客服系統",
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
