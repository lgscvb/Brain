# Claude Code 指令

請在 Brain 環境中執行以下指令：

---

## 專案說明

我要建立一個「全通路訊息管理平台」叫做 Brain，用於 Hour Jungle 共享辦公室的客服管理。

**核心功能：**
1. 接收 LINE@ 訊息（Webhook）
2. AI 自動產生回覆草稿（Claude API）
3. 人工審核後才發送
4. 記錄修改差異，用於持續學習優化

**重要：這不是自動回覆機器人，一定要人工審核才能發送。**

---

## 技術要求

- 後端：Python FastAPI
- 前端：React + Tailwind CSS（深色主題）
- 資料庫：SQLite（先用這個，之後再遷移）
- AI：Claude API (claude-3-haiku)
- Port：**8787**（不要用 8000）

---

## 請按照以下順序執行

### Step 1：建立專案結構

```
brain/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── api/routes/
│   ├── channels/
│   ├── brain/
│   ├── db/
│   └── services/
├── frontend/
│   └── (React Vite 專案)
├── .env.example
├── README.md
└── docker-compose.yml
```

### Step 2：建立後端

依照 TASKS.md 的 Phase 2 建立所有後端檔案。

關鍵檔案：
- `db/models.py` - Message, Draft, Response 三個表
- `services/claude_client.py` - Claude API 封裝
- `services/line_client.py` - LINE SDK 封裝
- `brain/prompts.py` - Prompt 模板（含 Hour Jungle 業務知識）
- `brain/draft_generator.py` - 草稿生成
- `channels/line_oa.py` - LINE Webhook 處理
- `api/routes/` - RESTful API

### Step 3：建立前端

用 Vite + React + Tailwind 建立深色主題的 Dashboard：
- 左側：待處理訊息列表
- 中間：訊息詳情 + AI 草稿 + 編輯區 + 發送按鈕
- 右側：手動新增訊息 + 學習記錄

### Step 4：測試

```bash
# 後端
cd backend
uvicorn main:app --reload --port 8787

# 前端
cd frontend
npm run dev

# ngrok
ngrok http 8787
```

---

## Hour Jungle 業務知識（寫入 Prompt）

- 虛擬登記地址：$10,000/月
- 共享辦公室：$5,000/月起
- 獨立辦公室：$12,000/月起
- 地址：台中市西區大忠南街55號7F-5
- 特色：會計師+律師團隊、最快7天完成登記、99.7%成功率

---

## 注意事項

1. Port 用 8787，不要用 8000
2. 先用 SQLite，不要用 PostgreSQL
3. 前端要深色主題（bg-gray-900）
4. 一定要有「修改記錄」功能（學習用）
5. LINE 回覆要用 push_message，不是 reply_message（因為是非同步處理）

---

開始吧！
