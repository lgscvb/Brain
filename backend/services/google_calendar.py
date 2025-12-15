"""
Brain - Google Calendar 服務
處理會議室預約的日曆整合
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendarService:
    """Google Calendar API 服務"""

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self, credentials_path: Optional[str] = None):
        """
        初始化 Google Calendar 服務

        Args:
            credentials_path: Service Account JSON 路徑
        """
        from config import settings

        self.service = None
        self.credentials_path = (
            credentials_path or
            settings.GOOGLE_CALENDAR_CREDENTIALS or
            os.getenv('GOOGLE_CALENDAR_CREDENTIALS')
        )

        if self.credentials_path and os.path.exists(self.credentials_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=self.SCOPES
                )
                self.service = build('calendar', 'v3', credentials=credentials)
                print(f"✅ Google Calendar 服務已初始化")
            except Exception as e:
                print(f"⚠️ Google Calendar 初始化失敗: {e}")
        else:
            print(f"⚠️ Google Calendar credentials 未設定或檔案不存在")

    def is_available(self) -> bool:
        """檢查服務是否可用"""
        return self.service is not None

    async def get_busy_times(
        self,
        calendar_id: str,
        date: str,
        timezone: str = "Asia/Taipei"
    ) -> List[Dict]:
        """
        取得指定日期的忙碌時段

        Args:
            calendar_id: Google Calendar ID
            date: 日期 (YYYY-MM-DD)
            timezone: 時區

        Returns:
            忙碌時段列表 [{"start": "09:00", "end": "10:00"}, ...]
        """
        if not self.service:
            return []

        try:
            # 設定時間範圍（當天 00:00 ~ 23:59）
            time_min = f"{date}T00:00:00+08:00"
            time_max = f"{date}T23:59:59+08:00"

            # 查詢事件
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            busy_times = []

            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                # 解析時間
                if 'T' in start:
                    start_time = start[11:16]  # 取 HH:MM
                    end_time = end[11:16]
                    busy_times.append({
                        "start": start_time,
                        "end": end_time,
                        "summary": event.get('summary', '已預約')
                    })

            return busy_times

        except HttpError as e:
            print(f"❌ 查詢日曆失敗: {e}")
            return []

    async def create_event(
        self,
        calendar_id: str,
        date: str,
        start_time: str,
        end_time: str,
        summary: str,
        description: str = "",
        timezone: str = "Asia/Taipei"
    ) -> Optional[str]:
        """
        建立日曆事件

        Args:
            calendar_id: Google Calendar ID
            date: 日期 (YYYY-MM-DD)
            start_time: 開始時間 (HH:MM)
            end_time: 結束時間 (HH:MM)
            summary: 事件標題
            description: 事件描述
            timezone: 時區

        Returns:
            事件 ID 或 None
        """
        if not self.service:
            print("⚠️ Google Calendar 服務未初始化，跳過建立事件")
            return None

        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': f"{date}T{start_time}:00",
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': f"{date}T{end_time}:00",
                    'timeZone': timezone,
                },
            }

            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            event_id = created_event.get('id')
            print(f"✅ 日曆事件已建立: {event_id}")
            return event_id

        except HttpError as e:
            print(f"❌ 建立日曆事件失敗: {e}")
            return None

    async def delete_event(
        self,
        calendar_id: str,
        event_id: str
    ) -> bool:
        """
        刪除日曆事件

        Args:
            calendar_id: Google Calendar ID
            event_id: 事件 ID

        Returns:
            是否成功
        """
        if not self.service:
            return False

        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            print(f"✅ 日曆事件已刪除: {event_id}")
            return True

        except HttpError as e:
            print(f"❌ 刪除日曆事件失敗: {e}")
            return False

    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        date: str,
        start_time: str,
        end_time: str,
        summary: str = None,
        description: str = None,
        timezone: str = "Asia/Taipei"
    ) -> bool:
        """
        更新日曆事件

        Returns:
            是否成功
        """
        if not self.service:
            return False

        try:
            # 先取得現有事件
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # 更新時間
            event['start'] = {
                'dateTime': f"{date}T{start_time}:00",
                'timeZone': timezone,
            }
            event['end'] = {
                'dateTime': f"{date}T{end_time}:00",
                'timeZone': timezone,
            }

            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description

            self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            print(f"✅ 日曆事件已更新: {event_id}")
            return True

        except HttpError as e:
            print(f"❌ 更新日曆事件失敗: {e}")
            return False


# 全域實例
_calendar_service: Optional[GoogleCalendarService] = None


def get_calendar_service() -> GoogleCalendarService:
    """取得 Google Calendar 服務單例"""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
    return _calendar_service
