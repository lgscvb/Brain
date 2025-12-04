"""
Brain - 日誌管理 API 路由
提供日誌查詢功能
"""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class LogEntry(BaseModel):
    """日誌條目"""
    timestamp: str
    level: str
    logger: str
    message: str
    line_number: int


class LogResponse(BaseModel):
    """日誌回應"""
    logs: List[LogEntry]
    total: int
    file: str


def get_log_file_path(log_type: str = "main") -> Path:
    """取得日誌檔案路徑"""
    backend_dir = Path(__file__).parent.parent.parent  # /app
    # Docker 環境日誌在 /app/logs
    log_dir = backend_dir / "logs"
    
    if log_type == "error":
        return log_dir / "error.log"
    else:
        return log_dir / "brain.log"


def parse_log_line(line: str, line_number: int) -> Optional[LogEntry]:
    """解析日誌行"""
    try:
        # 格式：2025-12-01 16:00:00 - logger_name - LEVEL - message
        parts = line.split(" - ", 3)
        if len(parts) >= 4:
            return LogEntry(
                timestamp=parts[0],
                logger=parts[1],
                level=parts[2],
                message=parts[3].strip(),
                line_number=line_number
            )
    except Exception:
        pass
    return None


@router.get("/logs", response_model=LogResponse)
async def get_logs(
    log_type: str = Query("main", description="日誌類型 (main/error)"),
    limit: int = Query(100, description="回傳筆數", le=1000),
    level: Optional[str] = Query(None, description="篩選等級 (INFO/WARNING/ERROR)"),
    search: Optional[str] = Query(None, description="搜尋關鍵字")
):
    """
    取得日誌記錄
    
    Args:
        log_type: 日誌類型 (main/error)
        limit: 回傳筆數
        level: 篩選日誌等級
        search: 搜尋關鍵字
    """
    log_file = get_log_file_path(log_type)
    
    if not log_file.exists():
        return LogResponse(logs=[], total=0, file=str(log_file))
    
    # 讀取日誌檔案
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return LogResponse(
            logs=[LogEntry(
                timestamp=datetime.now().isoformat(),
                level="ERROR",
                logger="system",
                message=f"讀取日誌失敗: {str(e)}",
                line_number=0
            )],
            total=1,
            file=str(log_file)
        )
    
    # 解析日誌（從最新到最舊）
    log_entries = []
    for i, line in enumerate(reversed(lines), 1):
        if not line.strip():
            continue
            
        entry = parse_log_line(line.strip(), len(lines) - i + 1)
        if entry:
            # 篩選等級
            if level and entry.level != level:
                continue
            
            # 搜尋關鍵字
            if search and search.lower() not in entry.message.lower():
                continue
            
            log_entries.append(entry)
            
            # 限制數量
            if len(log_entries) >= limit:
                break
    
    return LogResponse(
        logs=log_entries,
        total=len(log_entries),
        file=str(log_file)
    )


@router.get("/logs/stats")
async def get_log_stats():
    """取得日誌統計"""
    main_log = get_log_file_path("main")
    error_log = get_log_file_path("error")
    
    stats = {
        "main_log": {
            "exists": main_log.exists(),
            "size": main_log.stat().st_size if main_log.exists() else 0,
            "path": str(main_log)
        },
        "error_log": {
            "exists": error_log.exists(),
            "size": error_log.stat().st_size if error_log.exists() else 0,
            "path": str(error_log)
        }
    }
    
    # 計算行數
    if main_log.exists():
        try:
            with open(main_log, 'r', encoding='utf-8') as f:
                stats["main_log"]["lines"] = sum(1 for _ in f)
        except:
            stats["main_log"]["lines"] = 0
    
    if error_log.exists():
        try:
            with open(error_log, 'r', encoding='utf-8') as f:
                stats["error_log"]["lines"] = sum(1 for _ in f)
        except:
            stats["error_log"]["lines"] = 0
    
    return stats


@router.delete("/logs/clear")
async def clear_logs(log_type: str = Query("main", description="日誌類型 (main/error)")):
    """清空日誌檔案"""
    log_file = get_log_file_path(log_type)
    
    try:
        if log_file.exists():
            log_file.write_text("")
        return {"success": True, "message": f"{log_type} 日誌已清空"}
    except Exception as e:
        return {"success": False, "message": f"清空失敗: {str(e)}"}
