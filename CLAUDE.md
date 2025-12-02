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
   gcloud compute ssh lgscvbatter@brain-instance \
     --zone=asia-east1-b \
     --project=YOUR_PROJECT_ID \
     --command="cd /home/lgscvbatter/Brain && git pull origin main && docker compose build && docker compose up -d"
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
- **COMPLEX** (複雜任務) → Smart Model (Claude 3.5 Sonnet, $3/$15 per MTok)
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
MODEL_SMART=anthropic/claude-3.5-sonnet
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
