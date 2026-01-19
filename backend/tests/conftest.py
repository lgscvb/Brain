"""
Brain Test Configuration

【測試資料庫清理機制】
1. 每個測試函數結束後：drop_all 刪除所有表格資料
2. 整個測試 Session 結束後：刪除 test.db 檔案（如果使用檔案型 SQLite）

這確保測試不會留下任何 mock data。
"""
import os
import sys
import pytest
import atexit
from pathlib import Path
from typing import AsyncGenerator

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 測試資料庫檔案路徑
TEST_DB_PATH = Path(__file__).parent.parent / "test.db"

# Set test environment - 使用環境變數或預設值
# CI 環境會透過 .env.test 設定 DATABASE_URL
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
if "ADMIN_PASSWORD" not in os.environ:
    os.environ["ADMIN_PASSWORD"] = "test123"
if "AI_PROVIDER" not in os.environ:
    os.environ["AI_PROVIDER"] = "openrouter"
if "OPENROUTER_API_KEY" not in os.environ:
    os.environ["OPENROUTER_API_KEY"] = "test-key"

from main import app
from db.database import Base, get_db


# Test database setup - 優先使用環境變數
TEST_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

# SQLite 需要特殊處理
connect_args = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args=connect_args)
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database dependency for testing"""
    async with TestSessionLocal() as session:
        yield session


# Apply override
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def admin_headers():
    """Headers with admin password"""
    return {"X-Admin-Password": "test123"}


# ============================================================
# 測試結束清理機制
# ============================================================

def cleanup_test_database():
    """
    清理測試資料庫檔案

    【執行時機】
    - pytest session 結束時（透過 atexit 註冊）
    - 僅清理使用檔案型 SQLite 的情況

    【為什麼需要這個】
    雖然 drop_all 會清空表格，但 SQLite 檔案本身仍會留在磁碟
    長期累積會佔用空間，且可能導致下次測試讀到舊資料
    """
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
            print(f"\n🧹 測試資料庫已清理: {TEST_DB_PATH}")
        except Exception as e:
            print(f"\n⚠️ 清理測試資料庫失敗: {e}")


# 註冊清理函數（程式結束時執行）
atexit.register(cleanup_test_database)


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_all_tests(request):
    """
    Session 結束後清理測試資料庫

    【autouse=True】
    自動在每個測試 session 啟用，不需要手動引用

    【為什麼用 fixture 而不是只用 atexit】
    1. fixture 可以在 pytest 框架內正確執行
    2. 可以搭配 pytest 的 session scope 精確控制時機
    3. atexit 是備用方案（萬一 fixture 沒執行到）
    """
    yield  # 等待所有測試執行完畢
    # Session 結束後清理
    cleanup_test_database()
