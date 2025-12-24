# Brain AI 客服系統

> Hour Jungle AI 輔助客服系統，部署於 `brain.yourspce.org`

## 專案概述

Brain 是 Hour Jungle 的 AI 輔助客服系統，採用 LLM Routing 架構降低 AI 成本。

## 技術棧

- **後端**: Python 3.11+ / FastAPI
- **前端**: React + Vite + Tailwind CSS
- **資料庫**: SQLite (開發/生產均使用)
- **AI**: OpenRouter (推薦) / Anthropic 直連
- **部署**: Docker + GCP Compute Engine + Cloudflare Tunnel

---

## Hour Jungle 專案整合

### 專案關係 (V2 架構)

```
Hour Jungle 生態系統 (V2)
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────┐                                           │
│  │   v2-hj-crm      │  ← Monorepo                               │
│  │  ├─ frontend/    │────→ hj-v2.pages.dev (Cloudflare Pages)   │
│  │  └─ backend/     │────→ api-v2.yourspce.org (GCP VM)         │
│  └──────────────────┘                                           │
│           │                                                     │
│           │ CRM API 調用                                        │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │      brain       │────→ brain.yourspce.org (GCP VM)          │
│  │   (AI 客服系統)   │                                           │
│  └──────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### CRM 整合

Brain 透過 `JungleClient` 連接 CRM：

```python
# backend/services/jungle_client.py

# 查詢客戶資料
customer = await jungle_client.get_customer_by_line_id(line_user_id)

# 取得合約狀態
contracts = await jungle_client.get_customer_contracts(customer_id)

# 取得繳費狀態
payments = await jungle_client.get_pending_payments(customer_id)
```

### 環境變數（CRM 整合）

```env
CRM_API_URL=https://auto.yourspce.org
ENABLE_JUNGLE_INTEGRATION=true
```

**注意**：`auto.yourspce.org` 和 `api-v2.yourspce.org` 連接同一資料庫，目前 Brain 使用 `auto.yourspce.org` 是正確的。

---

## 檔案結構

```
brain/
├── backend/           # FastAPI 後端
│   ├── api/routes/    # API 路由
│   ├── brain/         # AI 邏輯 (router, draft_generator, prompts)
│   ├── db/            # 資料庫模型
│   └── services/      # 外部服務客戶端
├── frontend/          # React 前端
│   └── src/pages/     # 頁面組件
├── docker-compose.yml
└── .env               # 環境變數 (不提交)
```

---

## LLM Routing 架構

### 模型分流策略

- **SIMPLE** (簡單任務) → Fast Model (Gemini Flash, $0.075/$0.30 per MTok)
  - 問候、地址查詢、簡單回覆
- **COMPLEX** (複雜任務) → Smart Model (Claude Sonnet 4.5, $3/$15 per MTok)
  - 稅務諮詢、SPIN 銷售、複雜邏輯

### 相關檔案

- `backend/brain/prompts.py` - ROUTER_PROMPT 分流判斷
- `backend/brain/draft_generator.py` - 草稿生成邏輯
- `backend/services/claude_client.py` - AI 客戶端 (OpenRouter/Anthropic)
- `backend/api/routes/settings.py` - 設定 API
- `frontend/src/pages/SettingsPage.jsx` - 設定頁面 UI

---

## 環境變數

```env
# AI Provider
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-xxx

# LLM Routing
ENABLE_ROUTING=true
MODEL_SMART=anthropic/claude-sonnet-4.5
MODEL_FAST=google/gemini-flash-1.5

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=xxx
LINE_CHANNEL_SECRET=xxx

# CRM 整合
CRM_API_URL=https://auto.yourspce.org
ENABLE_JUNGLE_INTEGRATION=true
```

---

## 部署

### 快速部署

```bash
# 推送程式碼
cd brain
git add . && git commit -m "feat: 描述" && git push

# SSH 到 VM 並更新
gcloud compute ssh --zone "us-west1-b" "brain-ai-system" \
  --project "gen-lang-client-0281456461" \
  --command="cd ~/Brain && git pull && docker compose build && docker compose up -d"
```

### GCP VM 資訊

| 項目 | 值 |
|------|-----|
| VM 名稱 | `brain-ai-system` |
| 區域 | `us-west1-b` |
| GCP 專案 | `gen-lang-client-0281456461` |
| 域名 | `brain.yourspce.org` (Cloudflare Tunnel) |

### 部署架構

```
┌─────────────────────────────────────────────────────────┐
│                Cloudflare (DNS + SSL + Tunnel)          │
│                    brain.yourspce.org                   │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              GCP Compute Engine VM                      │
│              brain-ai-system (us-west1-b)               │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Docker Compose                                    │ │
│  │  ├─ nginx (80) → 前端靜態檔案                     │ │
│  │  └─ backend (8000) → FastAPI                      │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  資料存儲：                                             │
│  └─ ./data/brain.db (SQLite)                           │
└─────────────────────────────────────────────────────────┘
```

---

## 本地開發

```bash
# 後端
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

### Docker 本地測試

```bash
docker compose up -d
docker compose logs -f backend
```

### API 文檔

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /api/messages` | 訊息列表 |
| `POST /api/messages/{id}/generate-drafts` | AI 草稿生成 |
| `POST /api/messages/{id}/send` | 發送回覆 |
| `GET /api/usage` | API 用量統計 |
| `GET /api/usage/errors` | 錯誤記錄查詢 |
| `POST /webhook/line` | LINE Webhook |

---

## LINE Bot 配置

### Webhook 端點

```
POST /webhook/line
```

處理流程：
```
LINE → Webhook → 建立 Message → AI 生成草稿 → 人工審核 → 發送回覆
```

### LINE Developers Console 設定

| 項目 | 值 |
|------|-----|
| Webhook URL | `https://brain.yourspce.org/webhook/line` |
| Use webhook | ✅ 啟用 |
| Auto-reply | ❌ 關閉 |
| Greeting | ❌ 關閉 |

---

## Commit Message 規範

- `feat:` 新功能
- `fix:` 修復 bug
- `docs:` 文檔更新
- `refactor:` 重構
- `style:` 樣式調整
- `perf:` 效能優化

---

## 注意事項

1. **API Key 安全**: 絕對不要提交 `.env` 檔案
2. **資料庫**: Brain 使用自己的 SQLite（brain.db），不是連接 CRM 的 PostgreSQL
3. **成本監控**: 定期檢查 OpenRouter 用量避免超支
4. **語言規定**: 所有輸出必須使用繁體中文

---

## 相關專案

| 專案 | 路徑 | 說明 |
|------|------|------|
| v2-hj-crm | `../v2-hj-crm/` | CRM V2 Monorepo (frontend + backend) |

請參考 `../CLAUDE.md` 了解完整的專案架構
