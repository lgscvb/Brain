"""
Migration 001: 新增 Draft 回饋欄位
支援 AI 自我進化系統

執行方式：
cd /Users/daihaoting_1/Desktop/code/brain/backend
python -m db.migrations.001_add_draft_feedback_fields
"""
import sqlite3
import os

def migrate():
    """執行 migration"""
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "brain.db")
    db_path = os.path.abspath(db_path)

    print(f"正在連接資料庫: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 檢查欄位是否已存在
    cursor.execute("PRAGMA table_info(drafts)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    print(f"現有欄位: {existing_columns}")

    # 要新增的欄位
    new_columns = [
        ("is_good", "BOOLEAN"),
        ("rating", "INTEGER"),
        ("feedback_reason", "TEXT"),
        ("feedback_at", "DATETIME"),
        ("auto_analysis", "TEXT"),
        ("improvement_tags", "JSON"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            sql = f"ALTER TABLE drafts ADD COLUMN {col_name} {col_type}"
            print(f"執行: {sql}")
            cursor.execute(sql)
        else:
            print(f"欄位 {col_name} 已存在，跳過")

    conn.commit()
    conn.close()

    print("✅ Migration 完成！")


def rollback():
    """SQLite 不支援 DROP COLUMN，需要重建表格"""
    print("⚠️ SQLite 不支援 DROP COLUMN")
    print("如需回滾，請手動重建表格或還原備份")


if __name__ == "__main__":
    migrate()
