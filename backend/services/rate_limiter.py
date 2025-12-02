"""
Brain - 速率限制與防洗頻服務
防止惡意用戶短時間內發送大量訊息浪費 AI Token
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from collections import defaultdict
import hashlib
from config import settings


class RateLimiter:
    """
    速率限制器 - 防洗頻機制

    功能：
    1. 速率限制：同一用戶在時間窗口內的訊息數量限制
    2. 重複內容檢測：短時間內發送相同內容
    3. 冷卻機制：超過限制後需等待一段時間
    4. 黑名單：可手動封鎖惡意用戶
    """

    def __init__(self):
        # 用戶訊息記錄: {user_id: [(timestamp, content_hash), ...]}
        self._user_messages: Dict[str, list] = defaultdict(list)

        # 用戶冷卻時間: {user_id: cooldown_until}
        self._cooldowns: Dict[str, datetime] = {}

        # 黑名單: {user_id: reason}
        self._blacklist: Dict[str, str] = {}

        # 違規計數: {user_id: count}
        self._violation_count: Dict[str, int] = defaultdict(int)

    def _hash_content(self, content: str) -> str:
        """計算內容的 hash 值"""
        return hashlib.md5(content.strip().lower().encode()).hexdigest()[:16]

    def _clean_old_records(self, user_id: str):
        """清理過期的訊息記錄"""
        now = datetime.utcnow()
        window = timedelta(seconds=settings.RATE_LIMIT_WINDOW)

        self._user_messages[user_id] = [
            (ts, h) for ts, h in self._user_messages[user_id]
            if now - ts < window
        ]

    def check_rate_limit(self, user_id: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        檢查是否超過速率限制

        Args:
            user_id: 用戶 ID
            content: 訊息內容

        Returns:
            (is_allowed, reason): 是否允許發送，拒絕原因
        """
        now = datetime.utcnow()

        # 1. 檢查黑名單
        if user_id in self._blacklist:
            return False, f"blocked:{self._blacklist[user_id]}"

        # 2. 檢查冷卻時間
        if user_id in self._cooldowns:
            cooldown_until = self._cooldowns[user_id]
            if now < cooldown_until:
                remaining = (cooldown_until - now).seconds
                return False, f"cooldown:{remaining}s"
            else:
                # 冷卻結束，清除記錄
                del self._cooldowns[user_id]

        # 3. 清理過期記錄
        self._clean_old_records(user_id)

        # 4. 檢查速率限制
        message_count = len(self._user_messages[user_id])
        if message_count >= settings.RATE_LIMIT_MAX_MESSAGES:
            # 超過限制，進入冷卻
            self._violation_count[user_id] += 1
            cooldown_seconds = settings.RATE_LIMIT_COOLDOWN * self._violation_count[user_id]
            self._cooldowns[user_id] = now + timedelta(seconds=cooldown_seconds)
            return False, f"rate_limit:{settings.RATE_LIMIT_MAX_MESSAGES}/{settings.RATE_LIMIT_WINDOW}s"

        # 5. 檢查重複內容
        content_hash = self._hash_content(content)
        recent_hashes = [h for _, h in self._user_messages[user_id]]

        duplicate_count = recent_hashes.count(content_hash)
        if duplicate_count >= settings.RATE_LIMIT_MAX_DUPLICATES:
            self._violation_count[user_id] += 1
            cooldown_seconds = settings.RATE_LIMIT_COOLDOWN * self._violation_count[user_id]
            self._cooldowns[user_id] = now + timedelta(seconds=cooldown_seconds)
            return False, f"duplicate:{duplicate_count}"

        # 6. 記錄此次訊息
        self._user_messages[user_id].append((now, content_hash))

        # 7. 如果一切正常，減少違規計數（獎勵良好行為）
        if self._violation_count[user_id] > 0:
            self._violation_count[user_id] = max(0, self._violation_count[user_id] - 0.1)

        return True, None

    def add_to_blacklist(self, user_id: str, reason: str = "manual"):
        """將用戶加入黑名單"""
        self._blacklist[user_id] = reason
        print(f"🚫 用戶 {user_id[:20]}... 已加入黑名單: {reason}")

    def remove_from_blacklist(self, user_id: str):
        """將用戶從黑名單移除"""
        if user_id in self._blacklist:
            del self._blacklist[user_id]
            print(f"✅ 用戶 {user_id[:20]}... 已從黑名單移除")

    def get_user_status(self, user_id: str) -> Dict:
        """取得用戶狀態"""
        now = datetime.utcnow()
        self._clean_old_records(user_id)

        status = {
            "user_id": user_id[:20] + "...",
            "is_blacklisted": user_id in self._blacklist,
            "blacklist_reason": self._blacklist.get(user_id),
            "is_in_cooldown": False,
            "cooldown_remaining": 0,
            "recent_messages": len(self._user_messages[user_id]),
            "violation_count": self._violation_count.get(user_id, 0)
        }

        if user_id in self._cooldowns:
            cooldown_until = self._cooldowns[user_id]
            if now < cooldown_until:
                status["is_in_cooldown"] = True
                status["cooldown_remaining"] = (cooldown_until - now).seconds

        return status

    def reset_user(self, user_id: str):
        """重置用戶的所有限制狀態"""
        if user_id in self._user_messages:
            del self._user_messages[user_id]
        if user_id in self._cooldowns:
            del self._cooldowns[user_id]
        if user_id in self._violation_count:
            del self._violation_count[user_id]
        # 不自動移除黑名單，需要手動操作
        print(f"🔄 用戶 {user_id[:20]}... 限制狀態已重置")


# 全域速率限制器實例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """取得速率限制器單例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
