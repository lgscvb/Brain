# Brain AI API Documentation

> Base URL: `https://brain.yourspce.org/api`

## Authentication

部分 API 需要管理員密碼驗證：
- Header: `X-Admin-Password: <password>`

---

## Health & System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | 系統健康檢查（詳細） |
| GET | `/health/simple` | 系統健康檢查（簡單） |
| GET | `/version` | 取得系統版本 |

---

## Messages (訊息管理)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/messages` | 取得訊息列表 |
| GET | `/messages/pending` | 取得待處理訊息 |
| GET | `/messages/{message_id}` | 取得單一訊息 |
| POST | `/messages` | 建立新訊息 |
| POST | `/messages/{message_id}/send` | 發送訊息回覆 |

### Query Parameters (GET /messages)
- `page`: 頁碼 (default: 1)
- `page_size`: 每頁筆數 (default: 20)
- `status`: 篩選狀態

---

## Settings (系統設定)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/settings` | 取得系統設定 | - |
| POST | `/settings` | 更新系統設定 | Required |
| GET | `/settings/models` | 取得可用 AI 模型 | - |
| GET | `/settings/webhook-url` | 取得 Webhook URL | - |
| POST | `/settings/verify-password` | 驗證管理員密碼 | - |

### POST /settings Body
```json
{
  "AI_PROVIDER": "openrouter",
  "OPENROUTER_API_KEY": "sk-xxx",
  "ENABLE_ROUTING": true,
  "MODEL_SMART": "anthropic/claude-sonnet-4.5",
  "MODEL_FAST": "google/gemini-flash-1.5",
  "AUTO_REPLY_MODE": false,
  "LINE_CHANNEL_ACCESS_TOKEN": "xxx",
  "LINE_CHANNEL_SECRET": "xxx"
}
```

---

## Statistics (統計資料)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | 取得系統統計 |
| GET | `/learning/recent` | 取得最近學習記錄 |

---

## Logs (日誌管理)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/logs` | 取得系統日誌 |
| GET | `/logs/stats` | 取得日誌統計 |
| DELETE | `/logs/clear` | 清除日誌 |

### Query Parameters (GET /logs)
- `level`: 日誌等級 (DEBUG/INFO/WARNING/ERROR)
- `limit`: 筆數限制

---

## Feedback (AI 回饋)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/drafts/{draft_id}/feedback` | 提交草稿回饋 |
| GET | `/drafts/{draft_id}/feedback` | 取得草稿回饋 |
| GET | `/feedback/stats` | 回饋統計 |
| GET | `/feedback/list` | 回饋列表 |
| GET | `/feedback/training-data` | 取得訓練數據 |

---

## Usage (API 用量)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/usage/stats` | API 用量統計 |
| GET | `/usage/recent` | 最近用量記錄 |

---

## Webhook

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook/line` | LINE Webhook 接收端點 |

---

## Response Format

### Success
```json
{
  "status": "success",
  "data": { ... }
}
```

### Error
```json
{
  "detail": "Error message"
}
```

---

## Status Codes

| Code | Description |
|------|-------------|
| 200 | 成功 |
| 400 | 請求錯誤 |
| 401 | 未授權 |
| 403 | 禁止存取 |
| 404 | 找不到資源 |
| 500 | 伺服器錯誤 |
