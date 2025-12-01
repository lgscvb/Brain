"""
Brain - 資料庫連接管理
提供非同步資料庫引擎與 Session
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from backend.config import settings
from backend.db.models import Base


# 建立非同步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in settings.DATABASE_URL else None,
)

# 建立 Session Factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    取得資料庫 Session（依賴注入用）
    
    使用方式：
    ```python
    @app.get("/items")
    async def read_items(db: AsyncSession = Depends(get_db)):
        ...
    ```
    """
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    """建立所有資料表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """刪除所有資料表（謹慎使用）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
