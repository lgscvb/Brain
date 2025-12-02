"""
Brain - 日誌配置
設定系統日誌記錄
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 建立 logs 資料夾 (在 backend 同層，Docker 內為 /app/logs)
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

# 日誌格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(log_level=logging.INFO):
    """設定日誌系統"""
    
    # 根 logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # 移除現有 handlers
    logger.handlers = []
    
    # Console Handler（輸出到終端）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler - 一般日誌（自動輪替）
    file_handler = RotatingFileHandler(
        log_dir / "brain.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # File Handler - 錯誤日誌
    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)
    
    return logger


# 建立 logger 實例
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """取得指定名稱的 logger"""
    return logging.getLogger(name)
