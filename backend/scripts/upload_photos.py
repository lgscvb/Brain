"""
Brain - 照片上傳腳本
將本地照片上傳到 Cloudflare R2，並根據檔名自動分類

分類規則：
- exterior（大樓外觀）：檔名含「外觀」「大樓」
- private_office（獨立辦公室）：檔名含「D辦」「E辦」「獨立辦公室」
- coworking（共享空間）：檔名含「共享空間」「櫃檯」
- facilities（設施）：檔名含「廁所」「事務機」

用法：
    cd backend
    python scripts/upload_photos.py /path/to/photos/folder
"""

import os
import sys
import asyncio
from pathlib import Path

# 加入父目錄到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.r2_client import get_r2_photo_client
from datetime import datetime


# 照片分類規則（依優先順序排列，越前面優先級越高）
# facilities 優先，因為「共享空間廁所」應該歸類為「設施」
CATEGORY_RULES_PRIORITY = [
    ("facilities", ["廁所", "事務機"]),
    ("private_office", ["D辦", "E辦", "獨立辦公室"]),
    ("coworking", ["共享空間", "櫃檯"]),
    ("exterior", ["外觀", "大樓", "明錩"]),
]

# 分類中文名稱
CATEGORY_NAMES = {
    "exterior": "大樓外觀",
    "private_office": "獨立辦公室",
    "coworking": "共享空間",
    "facilities": "設施",
    "other": "其他",
}

# 支援的圖片格式
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def classify_photo(file_name: str) -> str:
    """
    根據檔名自動分類照片（依優先順序）

    Args:
        file_name: 照片檔名

    Returns:
        分類 key
    """
    for category, keywords in CATEGORY_RULES_PRIORITY:
        for keyword in keywords:
            if keyword in file_name:
                return category
    return "other"


def get_photo_title(file_name: str, category: str) -> str:
    """
    根據檔名和分類產生顯示標題

    Args:
        file_name: 照片檔名
        category: 分類

    Returns:
        顯示標題
    """
    # 移除時間戳前綴（如果有的話）
    name = file_name

    # 移除副檔名
    name = os.path.splitext(name)[0]

    # 移除「拷貝」等字樣
    name = name.replace("拷貝", "").strip()

    # 如果名稱太長或不好看，用分類名稱
    if len(name) > 20 or name.startswith("_ANS"):
        return CATEGORY_NAMES.get(category, "Hour Jungle 空間")

    return name


def get_content_type(file_path: str) -> str:
    """取得 MIME 類型"""
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return content_types.get(ext, "image/jpeg")


async def upload_photos_from_folder(folder_path: str, dry_run: bool = False, auto_confirm: bool = False):
    """
    從資料夾上傳所有照片到 R2

    Args:
        folder_path: 照片資料夾路徑
        dry_run: 是否只預覽不上傳
    """
    folder = Path(folder_path)

    if not folder.exists():
        print(f"錯誤：資料夾不存在: {folder_path}")
        return

    # 取得所有照片檔案
    photo_files = []
    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
            photo_files.append(file)

    if not photo_files:
        print(f"資料夾中沒有找到支援的照片檔案")
        return

    print(f"找到 {len(photo_files)} 張照片")
    print()

    # 分類統計
    category_counts = {}

    # 預覽分類結果
    print("=" * 60)
    print("照片分類預覽")
    print("=" * 60)

    for photo_file in photo_files:
        category = classify_photo(photo_file.name)
        title = get_photo_title(photo_file.name, category)
        category_name = CATEGORY_NAMES.get(category, "其他")

        category_counts[category] = category_counts.get(category, 0) + 1

        print(f"[{category_name:8s}] {photo_file.name}")
        print(f"           → 標題: {title}")

    print()
    print("-" * 60)
    print("分類統計:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {CATEGORY_NAMES.get(cat, cat):12s}: {count} 張")
    print("-" * 60)

    if dry_run:
        print()
        print("（預覽模式，未實際上傳）")
        return

    # 確認上傳
    if not auto_confirm:
        print()
        confirm = input("確定要上傳這些照片嗎？(y/N): ").strip().lower()
        if confirm != 'y':
            print("已取消上傳")
            return

    # 開始上傳
    print()
    print("=" * 60)
    print("開始上傳照片")
    print("=" * 60)

    r2_client = get_r2_photo_client()

    if not r2_client.is_configured():
        print("錯誤：R2 未配置，請檢查環境變數")
        print("需要設定：R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
        return

    success_count = 0
    failed_count = 0
    uploaded_photos = []

    for i, photo_file in enumerate(photo_files, 1):
        category = classify_photo(photo_file.name)
        title = get_photo_title(photo_file.name, category)
        content_type = get_content_type(str(photo_file))

        print(f"[{i}/{len(photo_files)}] 上傳中: {photo_file.name}")

        result = r2_client.upload_photo(
            file_path=str(photo_file),
            category=category,
            title=title,
            content_type=content_type
        )

        if result["success"]:
            print(f"         ✅ 成功: {result['r2_path']}")
            success_count += 1
            uploaded_photos.append({
                "r2_path": result["r2_path"],
                "file_name": photo_file.name,
                "title": title,
                "category": category,
                "file_size": result["file_size"]
            })
        else:
            print(f"         ❌ 失敗: {result['error']}")
            failed_count += 1

    print()
    print("=" * 60)
    print("上傳完成！")
    print(f"  成功: {success_count} 張")
    print(f"  失敗: {failed_count} 張")
    print("=" * 60)

    # 輸出上傳結果（可用於初始化資料庫）
    if uploaded_photos:
        print()
        print("上傳的照片資訊（可用於初始化）：")
        print("-" * 60)
        for photo in uploaded_photos:
            print(f"Category: {photo['category']}")
            print(f"  R2 Path: {photo['r2_path']}")
            print(f"  Title: {photo['title']}")
            print()


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(
        description="上傳照片到 Cloudflare R2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
分類規則：
  - exterior（大樓外觀）：檔名含「外觀」「大樓」
  - private_office（獨立辦公室）：檔名含「D辦」「E辦」「獨立辦公室」
  - coworking（共享空間）：檔名含「共享空間」「櫃檯」
  - facilities（設施）：檔名含「廁所」「事務機」

範例：
  python scripts/upload_photos.py /path/to/photos
  python scripts/upload_photos.py /path/to/photos --dry-run
        """
    )

    parser.add_argument(
        "folder",
        help="照片資料夾路徑"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只預覽分類結果，不實際上傳"
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="跳過確認，直接上傳"
    )

    args = parser.parse_args()

    asyncio.run(upload_photos_from_folder(args.folder, dry_run=args.dry_run, auto_confirm=args.yes))


if __name__ == "__main__":
    main()
