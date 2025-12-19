"""
為缺少 embedding 的知識條目生成向量
"""
import asyncio
import sys
sys.path.insert(0, '/Users/daihaoting_1/Desktop/code/brain/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from db.models import KnowledgeChunk
from services.embedding_client import get_embedding_client

# 資料庫連線
DATABASE_URL = "sqlite+aiosqlite:///brain.db"


async def main():
    """為缺少 embedding 的知識條目生成向量"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    embedding_client = get_embedding_client()

    if not embedding_client.is_available():
        print("❌ Embedding 服務不可用，請檢查 API Key 設定")
        return

    async with async_session() as session:
        # 找出沒有 embedding 的條目
        result = await session.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.embedding_json.is_(None),
                KnowledgeChunk.is_active == True
            )
        )
        chunks = result.scalars().all()

        if not chunks:
            print("✅ 所有知識條目都已有 embedding")
            return

        print(f"📝 找到 {len(chunks)} 筆缺少 embedding 的知識條目")

        updated = 0
        failed = 0

        for i, chunk in enumerate(chunks, 1):
            print(f"   [{i}/{len(chunks)}] 處理: {chunk.content[:50]}...")

            embedding = await embedding_client.embed_text(chunk.content)

            if embedding:
                chunk.embedding_json = embedding
                updated += 1
            else:
                print(f"   ⚠️ 生成失敗: ID {chunk.id}")
                failed += 1

            # 每 10 筆提交一次
            if updated % 10 == 0:
                await session.commit()

        await session.commit()

        print(f"\n✅ 完成！成功: {updated}，失敗: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
