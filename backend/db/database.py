"""
Brain - 資料庫連接管理
提供非同步資料庫引擎與 Session
"""
import ssl as _ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from config import settings
from db.models import Base


# 建立非同步引擎
if "sqlite" in settings.DATABASE_URL:
    _connect_args = {"check_same_thread": False}
    _poolclass = StaticPool
elif "postgresql" in settings.DATABASE_URL:
    # Supabase 使用自簽憑證，需關閉驗證
    _ssl_ctx = _ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = _ssl.CERT_NONE
    _connect_args = {"ssl": _ssl_ctx}
    _poolclass = None
else:
    _connect_args = {}
    _poolclass = None

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_connect_args,
    **( {"poolclass": _poolclass} if _poolclass is not None else {} ),
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
