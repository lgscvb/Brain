"""
Brain Test Configuration
"""
import os
import sys
import pytest
from typing import AsyncGenerator

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set test environment - 使用環境變數或預設值
# CI 環境會透過 .env.test 設定 DATABASE_URL
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
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
