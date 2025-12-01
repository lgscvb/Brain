# 🧠 Brain - Hour Jungle 全通路訊息管理平台

## 專案概述

Brain 是 Hour Jungle 的 AI 輔助客服系統，核心功能是：
- 統一收集多管道訊息（LINE@、Email、電話、手動輸入）
- AI 自動產生回覆草稿
- 人工審核後發送
- 記錄修改差異，持續優化 AI

**重點：這不是自動回覆機器人，是「AI 輔助 + 人工審核」的工作流。**

---

## 技術棧

| 層級 | 技術 |
|-----|------|
| 後端 | Python 3.11+ / FastAPI |
| 前端 | React + Tailwind CSS |
| 資料庫 | SQLite（開發）→ PostgreSQL（生產） |
| AI | Claude API (Anthropic) |
| 訊息管道 | LINE Messaging API |
| 部署 | Docker / GCP Cloud Run |

---

## 專案結構

```
brain/
├── README.md
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
│
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 設定檔
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── messages.py     # 訊息 API
│   │   │   ├── drafts.py       # 草稿 API
│   │   │   ├── webhooks.py     # Webhook 處理
│   │   │   └── stats.py        # 統計 API
│   │   └── deps.py             # 依賴注入
│   │
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── line_oa.py          # LINE@ 整合
│   │   ├── email_imap.py       # Email IMAP（Phase 2）
│   │   └── phone_twilio.py     # 電話 Twilio（Phase 2）
│   │
│   ├── brain/
│   │   ├── __init__.py
│   │   ├── router.py           # 意圖分類
│   │   ├── draft_generator.py  # 草稿生成
│   │   ├── learning.py         # 學習引擎
│   │   └── prompts.py          # Prompt 模板
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py         # DB 連接
│   │   ├── models.py           # SQLAlchemy 模型
│   │   └── schemas.py          # Pydantic 結構
│   │
│   └── services/
│       ├── __init__.py
│       ├── claude_client.py    # Claude API
│       └── line_client.py      # LINE SDK
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   │
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       │
│       ├── components/
│       │   ├── Layout.jsx
│       │   ├── MessageList.jsx
│       │   ├── MessageCard.jsx
│       │   ├── DraftEditor.jsx
│       │   ├── StatsBar.jsx
│       │   └── ManualInput.jsx
│       │
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── History.jsx
│       │   └── Learning.jsx
│       │
│       ├── hooks/
│       │   ├── useMessages.js
│       │   └── useWebSocket.js
│       │
│       └── services/
│           └── api.js
│
└── scripts/
    ├── init_db.py
    └── seed_data.py
```

---

## 環境變數

```env
# .env.example

# Server
PORT=8787
HOST=0.0.0.0
DEBUG=true

# Database
DATABASE_URL=sqlite:///./brain.db
# DATABASE_URL=postgresql://user:pass@localhost/brain

# LINE
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
LINE_CHANNEL_SECRET=your_secret_here

# Claude AI
ANTHROPIC_API_KEY=your_api_key_here

# Frontend
VITE_API_URL=http://localhost:8787
```

---

## 快速啟動

### 開發環境

```bash
# 1. Clone
git clone <repo>
cd brain

# 2. 後端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env 填入 API keys

# 3. 初始化 DB
python scripts/init_db.py

# 4. 啟動後端
uvicorn main:app --reload --port 8787

# 5. 前端（另一個終端）
cd frontend
npm install
npm run dev

# 6. ngrok（另一個終端）
ngrok http 8787
# 複製 https URL 到 LINE Console Webhook
```

### Docker

```bash
docker-compose up -d
```

---

## API 端點

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/messages` | 取得訊息列表 |
| GET | `/api/messages/pending` | 取得待處理訊息 |
| GET | `/api/messages/{id}` | 取得單一訊息 |
| POST | `/api/messages` | 手動新增訊息 |
| POST | `/api/messages/{id}/send` | 發送回覆 |
| POST | `/api/messages/{id}/regenerate` | 重新生成草稿 |
| GET | `/api/stats` | 取得統計資料 |
| GET | `/api/learning/recent` | 取得最近學習記錄 |
| POST | `/webhook/line` | LINE Webhook |

---

## 核心流程

```
1. 訊息進入
   LINE@ Webhook → 儲存訊息 → 觸發草稿生成

2. AI 處理
   載入客戶資料 → 檢索知識庫 → 生成草稿 + 策略建議

3. 人工審核
   Dashboard 顯示 → 選擇/編輯草稿 → 按下發送

4. 學習記錄
   比對原始 vs 最終 → AI 分析修改原因 → 更新學習權重

5. 持續優化
   高頻修改模式 → 調整 Prompt → 提升採用率
```

---

## Hour Jungle 業務知識

### 服務項目
- 虛擬登記地址：$10,000/月
- 共享辦公室：$5,000/月起
- 獨立辦公室：$12,000/月起
- 會議室租借：$300/小時起

### 核心賣點
- 台中五權路金融商圈門牌
- 會計師 + 律師團隊
- 最快 7 天完成登記
- 99.7% 成功率
- 全額退費保證

### SPIN 銷售流程
- Situation：了解客戶現況（公司型態、人數、目前地址）
- Problem：挖掘痛點（租金壓力、地址不體面）
- Implication：放大影響（客戶觀感、信任度）
- Need-payoff：導向解決方案

---

## Phase 規劃

### Phase 1（當前）
- [x] LINE@ Webhook 整合
- [x] AI 草稿生成
- [x] Web Dashboard
- [x] 發送 + 修改記錄

### Phase 2
- [ ] Email IMAP 整合
- [ ] 電話 Twilio + Whisper
- [ ] CRM API 串接
- [ ] 完整學習循環

### Phase 3
- [ ] 維修派工單
- [ ] 線上合約簽署
- [ ] 自動催繳流程
