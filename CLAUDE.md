# Brain AI 客服系統 - Claude Code 開發規範

## 專案概述

Brain 是 Hour Jungle 的 AI 輔助客服系統，採用 LLM Routing 架構降低 AI 成本。

## 技術棧

- **後端**: Python 3.11+ / FastAPI
- **前端**: React + Vite + Tailwind CSS
- **資料庫**: SQLite (開發) / PostgreSQL (生產)
- **AI**: OpenRouter (推薦) / Anthropic 直連
- **部署**: Docker + GCP Compute Engine

---

## 自動化工作流程

### 每次修改程式碼後，必須執行以下步驟：

1. **Git 提交**
   ```bash
   cd /Users/daihaoting_1/Desktop/code/brain
   git add .
   git commit -m "feat/fix/docs: 簡短描述變更內容"
   git push origin main
   ```

2. **Docker 部署到 GCP VM**
   ```bash
   # SSH 到 GCP VM 並更新
   gcloud compute ssh --zone "us-west1-b" "brain-ai-system" \
     --command="cd ~/Brain && git pull origin main && docker compose build && docker compose up -d"
   ```

3. **驗證部署**
   - 前端: http://YOUR_VM_IP
   - API: http://YOUR_VM_IP:8000/docs

---

## 開發規範

### 檔案結構
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

### Commit Message 規範
- `feat:` 新功能
- `fix:` 修復 bug
- `docs:` 文檔更新
- `refactor:` 重構
- `style:` 樣式調整
- `perf:` 效能優化

### 程式碼風格
- Python: 遵循 PEP 8
- React: 函數式組件 + Hooks
- 中文註解優先

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

必要的環境變數 (參考 `.env.example`):

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
```

---

## 常用指令

### 本地開發
```bash
# 後端
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000

# 前端
cd frontend && npm run dev
```

### Docker 本地測試
```bash
docker compose up -d
docker compose logs -f
```

### 查看 API 文檔
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 注意事項

1. **API Key 安全**: 絕對不要提交 `.env` 檔案或在程式碼中硬編碼 API Key
2. **資料庫遷移**: 新增 model 欄位後需重建資料庫或執行遷移
3. **前端部署**: 修改前端後需重新 build Docker image
4. **成本監控**: 定期檢查 OpenRouter 用量避免超支

---

## Hour Jungle 專案整合

### 專案關係

Brain 是 Hour Jungle 生態系統的一部分：

```
┌──────────────┐    API調用    ┌──────────────────────┐
│ opus高級前端  │ ────────────→ │  hourjungle-crm      │
│ (CRM前端UI)   │              │  (MCP Server+DB)     │
└──────────────┘              └──────────────────────┘
                                      ↑
                                      │ Jungle整合
                                      │
                    ┌─────────────────┘
                    │
              ┌─────▼─────┐
              │   brain   │
              │ (AI客服)  │
              └───────────┘
```

### Jungle CRM 整合

Brain 透過 `JungleClient` 連接 hourjungle-crm：

```python
# backend/services/jungle_client.py

# 查詢客戶資料
customer = await jungle_client.get_customer_by_line_id(line_user_id)

# 取得合約狀態
contracts = await jungle_client.get_customer_contracts(customer_id)

# 取得繳費狀態
payments = await jungle_client.get_pending_payments(customer_id)
```

### 環境變數（Jungle 整合）

```env
# Jungle CRM API
JUNGLE_API_URL=https://auto.yourspce.org
JUNGLE_API_KEY=xxx
ENABLE_JUNGLE_INTEGRATION=true
```

---

## 待完成功能

- [ ] 平面圖生成
- [ ] 必要文件生成
- [ ] 自動化測試
- [ ] 人工作業測試
- [ ] RAG 優化
- [ ] LLM Routing 調優
- [ ] 知識庫擴充

---

## 相關專案

| 專案 | 路徑 | 說明 |
|------|------|------|
| opus高級前端 | `../opus高級前端/` | CRM 管理後台 UI |
| hourjungle-crm | `../hourjungle-crm/` | MCP Server + PostgreSQL |

請參考 `../CLAUDE.md` 了解完整的專案架構和開發理念

---

## LINE Bot 配置

### Webhook 端點

```
POST /webhook/line
```

LINE Bot 訊息會透過此端點進入系統，處理流程：

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

### 對話狀態管理

Brain 使用記憶體/SQLite 儲存對話狀態（不使用 Redis）：

```python
# backend/db/models.py

class Message(Base):
    sender_id = Column(String)      # LINE user ID
    sender_name = Column(String)    # 顯示名稱
    content = Column(Text)          # 訊息內容
    status = Column(String)         # pending/drafted/sent/archived
```

### 取得對話歷史

```python
# 取得同一用戶的最近 N 則對話
messages = await get_conversation_history(
    sender_id=line_user_id,
    limit=CONVERSATION_HISTORY_LIMIT  # 預設 30
)
```

---

## GCP 部署配置

### 部署架構

```
┌─────────────────────────────────────────────────────────┐
│                    Cloudflare (DNS + SSL)               │
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
│  │  └─ backend (8000/8787) → FastAPI                 │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  資料存儲：                                             │
│  └─ ./data/brain.db (SQLite)                           │
└─────────────────────────────────────────────────────────┘
```

### VM 資訊

| 項目 | 值 |
|------|-----|
| VM 名稱 | `brain-ai-system` |
| 區域 | `us-west1-b` |
| 機器類型 | `e2-small` 或 `e2-medium` |
| 作業系統 | Ubuntu 22.04 LTS |

### 部署指令

```bash
# 1. SSH 到 VM
gcloud compute ssh --zone "us-west1-b" "brain-ai-system"

# 2. 進入專案目錄並更新
cd ~/Brain
git pull origin main

# 3. 重建並啟動
docker compose build
docker compose up -d

# 4. 查看日誌
docker compose logs -f backend
```

### 一鍵部署腳本

```bash
# 從本地執行
gcloud compute ssh --zone "us-west1-b" "brain-ai-system" \
  --command="cd ~/Brain && git pull origin main && docker compose build && docker compose up -d"
```

### Cloudflare 設定

| 項目 | 值 |
|------|-----|
| DNS Record | `brain` → GCP VM IP (A record) |
| Proxy | ✅ 啟用 (橘色雲朵) |
| SSL/TLS | Full (strict) |

### 環境變數檢查

確保 VM 上的 `.env` 包含：

```env
# AI Provider
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-xxx

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=xxx
LINE_CHANNEL_SECRET=xxx

# Jungle CRM 整合
CRM_API_URL=https://auto.yourspce.org
ENABLE_JUNGLE_INTEGRATION=true
```
