"""
Brain - Obsidian 知識庫匯入腳本
從 Obsidian Vault 的 Markdown 檔案匯入知識到 Brain RAG 系統

用法：
    # Dry Run（預覽，不實際寫入）
    python scripts/import_obsidian_knowledge.py /path/to/obsidian/vault --dry-run

    # 實際匯入
    python scripts/import_obsidian_knowledge.py /path/to/obsidian/vault

功能：
    1. 遞迴讀取 .md 檔案
    2. 按 ## 標題切塊（每塊獨立檢索）
    3. 提取 YAML frontmatter 作為 metadata
    4. 清理 Obsidian 特有語法（wikilinks、callouts）
    5. 去重檢查（content + category 完全相同則跳過）
    6. 生成 Embedding 並存入 knowledge_chunks 表
"""
import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# 添加專案根目錄到 path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 切換工作目錄到 backend，確保 .env 能被正確讀取
import os
os.chdir(backend_dir)

# 手動載入 .env（在 config 模組之前）
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ 載入環境變數: {env_path}")

import yaml
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from db.models import Base, KnowledgeChunk
from services.embedding_client import get_embedding_client
from config import settings


# =============================================================================
# 配置
# =============================================================================

# 分類映射：根據路徑自動判斷分類
CATEGORY_MAP = {
    "公司設立": "service_info",
    "稅務與風控": "faq",
    "特許行業": "service_info",
    "借址登記": "service_info",
    "勞健保": "faq",
    "銷售技巧": "tactics",
    "營運資訊": "service_info",
}

# 跳過的檔案（已有更完整版本在 sales_mindmap.json 或不適合作為知識庫）
SKIP_FILES = [
    "業務SOP.md",
    "銷售話術指南.md",
    "SPIN銷售法心智圖.md",
    "待辦事項.md",
    "README.md",
]

# 跳過的目錄（內部營運資料，不適合作為客服知識）
SKIP_DIRECTORIES = [
    "客戶遷出",      # 個別客戶案件
    "系統開發",      # 內部開發筆記
    "專案",          # 專案管理
    "會議紀錄",      # 內部會議
]

# 最小內容長度（太短的區塊沒有意義）
MIN_CONTENT_LENGTH = 50


# =============================================================================
# Markdown 解析
# =============================================================================

def sanitize_for_json(obj: Any) -> Any:
    """
    將物件轉換為 JSON 可序列化的格式

    處理：
    - datetime.date → ISO 字串
    - datetime.datetime → ISO 字串
    - 其他保持不變
    """
    from datetime import date, datetime

    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    return obj


def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    提取 YAML frontmatter

    Returns:
        (frontmatter_dict, remaining_content)
    """
    frontmatter = {}

    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                raw_frontmatter = yaml.safe_load(parts[1]) or {}
                # 將日期等不可序列化的類型轉換為字串
                frontmatter = sanitize_for_json(raw_frontmatter)
            except yaml.YAMLError:
                pass  # 解析失敗就略過
            content = parts[2]

    return frontmatter, content


def clean_obsidian_syntax(text: str) -> str:
    """
    清理 Obsidian 特有語法，保留核心內容

    處理：
    - [[wikilinks]] → 純文字
    - [[link|alias]] → alias
    - > [!tip] callout → 保留內容，移除語法
    - ![[embed]] → 移除
    - #tags → 移除
    """
    # 移除嵌入 ![[...]]
    text = re.sub(r'!\[\[([^\]]+)\]\]', '', text)

    # [[link|alias]] → alias
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)

    # [[wikilinks]] → 純文字
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)

    # 移除 callout 標記行 > [!xxx] xxx，但保留其後的引用內容
    text = re.sub(r'> \[!(\w+)\][^\n]*\n', '', text)

    # 移除行內 #tags（但保留標題的 #）
    text = re.sub(r'(?<!\n)#[\w\-]+(?:\s|$)', ' ', text)

    # 移除多餘空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def parse_markdown_to_chunks(file_path: Path) -> List[Dict[str, Any]]:
    """
    解析 Markdown 檔案，按 ## 標題切塊

    Returns:
        [
            {
                "content": "區塊內容",
                "title": "區塊標題",
                "source_file": "原始檔案名",
                "file_path": "完整路徑",
                "frontmatter": {...}  # Obsidian metadata
            }
        ]
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
    except Exception as e:
        print(f"   ⚠️ 無法讀取 {file_path}: {e}")
        return []

    # 1. 提取 frontmatter
    frontmatter, content = parse_frontmatter(raw_content)

    # 2. 按 ## 標題切塊
    chunks = []

    # 取得文件標題（# 開頭的第一行）
    doc_title = file_path.stem  # 預設用檔名
    title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
    if title_match:
        doc_title = title_match.group(1).strip()

    # 分割成 ## 區塊
    sections = re.split(r'\n## ', content)

    for i, section in enumerate(sections):
        if not section.strip():
            continue

        # 提取標題和內容
        lines = section.split('\n', 1)
        if i == 0:
            # 第一塊可能是文件開頭（# 標題之前或之後的內容）
            title = doc_title
            body = section
        else:
            title = lines[0].strip('#').strip()
            body = lines[1] if len(lines) > 1 else ""

        # 清理 Obsidian 語法
        body = clean_obsidian_syntax(body)

        # 過濾太短的區塊
        if len(body.strip()) < MIN_CONTENT_LENGTH:
            continue

        chunks.append({
            "content": body.strip(),
            "title": title,
            "doc_title": doc_title,
            "source_file": file_path.name,
            "file_path": str(file_path),
            "frontmatter": frontmatter
        })

    return chunks


def determine_category(file_path: Path) -> str:
    """根據檔案路徑判斷分類"""
    path_str = str(file_path)

    for keyword, category in CATEGORY_MAP.items():
        if keyword in path_str:
            return category

    # 預設分類
    return "service_info"


def determine_service_type(file_path: Path, content: str) -> Optional[str]:
    """根據檔案路徑和內容判斷服務類型"""
    path_str = str(file_path).lower()
    content_lower = content.lower()

    # 關鍵字判斷
    if any(kw in path_str or kw in content_lower for kw in ["借址", "登記地址", "address"]):
        return "address_service"
    if any(kw in path_str or kw in content_lower for kw in ["共享", "coworking", "共同工作"]):
        return "coworking"
    if any(kw in path_str or kw in content_lower for kw in ["辦公室", "office", "獨立辦公"]):
        return "private_office"
    if any(kw in path_str or kw in content_lower for kw in ["會議室", "meeting"]):
        return "meeting_room"

    return None


# =============================================================================
# 匯入器
# =============================================================================

class ObsidianImporter:
    """Obsidian 知識庫匯入器"""

    def __init__(self, session: Optional[AsyncSession] = None, dry_run: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.embedding_client = None if dry_run else get_embedding_client()
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.errors: List[str] = []

    async def import_from_vault(self, vault_path: str) -> Dict[str, Any]:
        """
        從 Obsidian vault 批量匯入知識

        Args:
            vault_path: Obsidian vault 路徑

        Returns:
            {"imported": N, "skipped": N, "errors": [...]}
        """
        vault = Path(vault_path)
        if not vault.exists():
            raise FileNotFoundError(f"找不到 Vault: {vault_path}")

        print(f"\n📂 掃描 Vault: {vault_path}")

        # 遞迴找所有 .md 檔案
        md_files = list(vault.rglob("*.md"))
        print(f"   找到 {len(md_files)} 個 Markdown 檔案")

        for md_file in md_files:
            # 跳過特定檔案
            if md_file.name in SKIP_FILES:
                print(f"⏭️  跳過（已有更完整版本）: {md_file.name}")
                self.skipped_count += 1
                continue

            # 跳過特定目錄
            if any(skip_dir in md_file.parts for skip_dir in SKIP_DIRECTORIES):
                print(f"⏭️  跳過（內部營運資料）: {md_file.relative_to(vault)}")
                self.skipped_count += 1
                continue

            # 跳過隱藏檔案和 .obsidian 目錄
            if any(part.startswith('.') for part in md_file.parts):
                continue

            # 解析並切塊
            chunks = parse_markdown_to_chunks(md_file)
            if not chunks:
                continue

            print(f"\n📄 處理: {md_file.relative_to(vault)}")

            for chunk in chunks:
                await self._add_chunk(
                    content=chunk["content"],
                    category=determine_category(md_file),
                    sub_category=chunk["title"],
                    service_type=determine_service_type(md_file, chunk["content"]),
                    metadata={
                        "source_file": chunk["source_file"],
                        "doc_title": chunk["doc_title"],
                        "file_path": chunk["file_path"],
                        "frontmatter": chunk["frontmatter"],
                        "import_source": "obsidian"
                    }
                )

        # 最終提交
        if not self.dry_run:
            await self.session.commit()

        return {
            "imported": self.imported_count,
            "skipped": self.skipped_count,
            "errors": self.errors
        }

    async def _add_chunk(
        self,
        content: str,
        category: str,
        sub_category: str = None,
        service_type: str = None,
        metadata: Dict = None
    ):
        """添加單個知識 chunk"""
        if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            self.skipped_count += 1
            return

        if self.dry_run:
            # Dry Run 模式不檢查資料庫重複
            print(f"   📝 [DRY RUN] 將匯入: {sub_category[:40] if sub_category else content[:40]}...")
            self.imported_count += 1
            return

        # 檢查是否已存在（content + category 相同視為重複）
        existing = await self.session.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.content == content,
                KnowledgeChunk.category == category
            )
        )
        if existing.scalar_one_or_none():
            print(f"   ⏭️  重複: {sub_category[:30] if sub_category else 'N/A'}...")
            self.skipped_count += 1
            return

        try:
            # 生成 Embedding
            embedding = await self.embedding_client.embed_text(content)

            chunk = KnowledgeChunk(
                content=content,
                category=category,
                sub_category=sub_category,
                service_type=service_type,
                extra_data=metadata or {},
                embedding_json=embedding,
                is_active=True
            )

            self.session.add(chunk)
            self.imported_count += 1

            # 每 50 個提交一次
            if self.imported_count % 50 == 0:
                await self.session.commit()
                print(f"   💾 已匯入 {self.imported_count} 條...")

            print(f"   ✅ 匯入: {sub_category[:40] if sub_category else content[:40]}...")

        except Exception as e:
            self.error_count += 1
            error_msg = f"{sub_category or content[:30]}: {e}"
            self.errors.append(error_msg)
            print(f"   ❌ 錯誤: {error_msg}")


# =============================================================================
# 主程式
# =============================================================================

async def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="從 Obsidian Vault 匯入知識到 Brain RAG 系統"
    )
    parser.add_argument(
        "vault_path",
        help="Obsidian Vault 路徑"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只預覽，不實際寫入資料庫"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Brain - Obsidian 知識庫匯入工具")
    if args.dry_run:
        print("🔍 模式: DRY RUN（預覽，不寫入）")
    else:
        print("💾 模式: 實際匯入")
    print("=" * 60)

    if args.dry_run:
        # Dry Run 模式：不需要資料庫連接
        importer = ObsidianImporter(session=None, dry_run=True)
        try:
            result = await importer.import_from_vault(args.vault_path)
        except FileNotFoundError as e:
            print(f"\n❌ 錯誤: {e}")
            return
    else:
        # 實際匯入模式：需要資料庫連接
        database_url = settings.DATABASE_URL
        # 轉換為 async driver
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("sqlite://") and "+aiosqlite" not in database_url:
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

        engine = create_async_engine(database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        # 確保表存在
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 執行匯入
        async with async_session() as session:
            importer = ObsidianImporter(session, dry_run=False)

            try:
                result = await importer.import_from_vault(args.vault_path)
            except FileNotFoundError as e:
                print(f"\n❌ 錯誤: {e}")
                return

        await engine.dispose()

    # 輸出結果
    print("\n" + "=" * 60)
    if args.dry_run:
        print("🔍 DRY RUN 完成（未實際寫入）")
    else:
        print("✅ 匯入完成!")
    print(f"   - {'將匯入' if args.dry_run else '成功匯入'}: {result['imported']} 條")
    print(f"   - 略過（重複/太短）: {result['skipped']} 條")
    if result['errors']:
        print(f"   - 錯誤: {len(result['errors'])} 條")
        for err in result['errors'][:5]:  # 只顯示前 5 個
            print(f"      • {err}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
