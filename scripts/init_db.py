#!/usr/bin/env python
"""
初始化資料庫
建立所有資料表
"""
import asyncio
import sys
from pathlib import Path

# 加入後端路徑到 sys.path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.db.database import create_tables


async def main():
    """主函數"""
    print("🔨 開始初始化資料庫...")
    try:
        await create_tables()
        print("✅ 資料庫初始化完成！")
    except Exception as e:
        print(f"❌ 資料庫初始化失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
