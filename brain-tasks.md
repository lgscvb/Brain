# Brain MVP - Task List

## 給 Claude Code 的指令

請按照以下順序建立專案，每完成一個 Task 就標記完成。

---

## Phase 1: 專案初始化

### Task 1.1: 建立專案結構
```
建立以下目錄結構：
brain/
├── backend/
│   ├── api/routes/
│   ├── channels/
│   ├── brain/
│   ├── db/
│   └── services/
├── frontend/src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   └── services/
└── scripts/
```

### Task 1.2: 建立後端 requirements.txt
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
line-bot-sdk>=3.5.0
anthropic>=0.7.0
sqlalchemy>=2.0.0
aiosqlite>=0.19.0
python-dotenv>=1.0.0
pydantic>=2.5.0
python-multipart>=0.0.6
```

### Task 1.3: 建立 .env.example
```env
# Server
PORT=8787
HOST=0.0.0.0
DEBUG=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./brain.db

# LINE
LINE_CHANNEL_ACCESS_TOKEN=
LINE_CHANNEL_SECRET=

# Claude AI
ANTHROPIC_API_KEY=
```

---

## Phase 2: 後端核心

### Task 2.1: 建立 backend/config.py
```python
設定檔，從環境變數讀取：
- PORT, HOST, DEBUG
- DATABASE_URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET
- ANTHROPIC_API_KEY
```

### Task 2.2: 建立 backend/db/models.py
```python
SQLAlchemy 模型：

class Message:
    id: int (PK)
    source: str  # line_oa, email, phone, manual
    sender_id: str
    sender_name: str
    content: str
    status: str  # pending, drafted, sent, archived
    priority: str  # high, medium, low
    created_at: datetime
    updated_at: datetime

class Draft:
    id: int (PK)
    message_id: int (FK)
    content: str
    strategy: str  # AI 策略說明
    intent: str  # 意圖分類
    is_selected: bool
    created_at: datetime

class Response:
    id: int (PK)
    message_id: int (FK)
    draft_id: int (FK, nullable)
    original_content: str  # AI 原始草稿
    final_content: str  # 實際發送內容
    is_modified: bool
    modification_reason: str  # AI 分析的修改原因
    sent_at: datetime
```

### Task 2.3: 建立 backend/db/database.py
```python
- 非同步 SQLAlchemy 引擎
- get_db() 依賴注入
- create_tables() 初始化
```

### Task 2.4: 建立 backend/db/schemas.py
```python
Pydantic schemas for API:
- MessageCreate, MessageRead, MessageList
- DraftRead
- ResponseCreate
- StatsRead
```

### Task 2.5: 建立 backend/services/claude_client.py
```python
Claude API 封裝：
- generate_draft(message, sender_name, source) -> dict
  回傳: {intent, strategy, draft, next_action}
- analyze_modification(original, final) -> str
  回傳: 修改原因分析
```

### Task 2.6: 建立 backend/services/line_client.py
```python
LINE SDK 封裝：
- send_text_message(user_id, text)
- get_user_profile(user_id) -> {display_name, user_id}
- verify_signature(body, signature) -> bool
```

### Task 2.7: 建立 backend/brain/prompts.py
```python
Prompt 模板：

DRAFT_PROMPT = """
你是 Hour Jungle 共享辦公室的客服助理。

## 客戶資訊
- 名稱：{sender_name}
- 來源：{source}

## 客戶訊息
{content}

## Hour Jungle 資訊
- 虛擬登記地址：$10,000/月（含信件代收、90天免費稅務法律諮詢）
- 共享辦公室：$5,000/月起
- 獨立辦公室：$12,000/月起
- 會議室：$300/小時起
- 地址：台中市西區大忠南街55號7F-5
- 特色：會計師+律師團隊、最快7天完成登記、99.7%成功率、全額退費保證

## 回覆原則
1. 親切、專業、簡潔
2. 適度使用 emoji（1-2個）
3. 如果是銷售機會，使用 SPIN 銷售法：
   - Situation: 了解現況
   - Problem: 挖掘痛點
   - Implication: 放大影響
   - Need-payoff: 導向解決方案
4. 每次只問一個問題
5. 目標是預約參觀或進一步諮詢

## 回傳 JSON
{{
    "intent": "詢價|預約|客訴|閒聊|報修|其他",
    "strategy": "回覆策略說明（給操作者看，20字內）",
    "draft": "回覆草稿內容",
    "next_action": "建議下一步行動"
}}
"""

MODIFICATION_ANALYSIS_PROMPT = """
比較 AI 原始草稿和人類修改後的版本，分析修改原因。

原始草稿：
{original}

修改後：
{final}

請簡短說明（30字內）：改了什麼 + 可能原因
"""
```

### Task 2.8: 建立 backend/brain/draft_generator.py
```python
草稿生成器：
- async generate(message_id, content, sender_name, source)
  1. 呼叫 Claude API
  2. 解析 JSON 回應
  3. 儲存到 drafts 表
  4. 更新 message status 為 'drafted'
```

### Task 2.9: 建立 backend/channels/line_oa.py
```python
LINE Webhook 處理：
- handle_webhook(body, signature)
- handle_message_event(event)
  1. 取得 user profile
  2. 儲存 message
  3. 背景觸發草稿生成
```

### Task 2.10: 建立 backend/api/routes/webhooks.py
```python
@router.post("/webhook/line")
async def line_webhook(request: Request, background_tasks: BackgroundTasks):
    - 驗證簽名
    - 處理事件
    - 回傳 200
```

### Task 2.11: 建立 backend/api/routes/messages.py
```python
@router.get("/messages")
- 取得所有訊息（可篩選 status）

@router.get("/messages/pending")
- 取得待處理訊息（含 draft）

@router.get("/messages/{id}")
- 取得單一訊息詳情

@router.post("/messages")
- 手動新增訊息（其他管道複製貼上用）
- 自動觸發草稿生成

@router.post("/messages/{id}/send")
- body: {content: str, draft_id: int?}
- 發送回覆（LINE push message）
- 記錄 response（含 is_modified, modification_reason）
- 更新 message status 為 'sent'

@router.post("/messages/{id}/regenerate")
- 重新生成草稿

@router.post("/messages/{id}/archive")
- 標記為已處理（不發送）
```

### Task 2.12: 建立 backend/api/routes/stats.py
```python
@router.get("/stats")
回傳：
- pending_count: 待處理數量
- today_sent: 今日已發送數量
- modification_rate: 修改率（%）
- avg_response_time: 平均回覆時間

@router.get("/learning/recent")
回傳最近 10 筆修改記錄：
- original_content
- final_content
- modification_reason
- created_at
```

### Task 2.13: 建立 backend/main.py
```python
FastAPI 應用：
- CORS 設定（允許 localhost:5173）
- 掛載 routes
- startup 事件：create_tables
- health check endpoint
```

---

## Phase 3: 前端

### Task 3.1: 初始化前端專案
```bash
cd frontend
npm create vite@latest . -- --template react
npm install tailwindcss postcss autoprefixer
npm install @heroicons/react axios date-fns react-router-dom
npx tailwindcss init -p
```

### Task 3.2: 設定 tailwind.config.js
```javascript
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### Task 3.3: 建立 frontend/src/index.css
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* 深色主題 */
body {
  @apply bg-gray-900 text-white;
}
```

### Task 3.4: 建立 frontend/src/services/api.js
```javascript
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8787';

export const api = {
  // Messages
  getPendingMessages: () => axios.get(`${API_URL}/api/messages/pending`),
  getMessage: (id) => axios.get(`${API_URL}/api/messages/${id}`),
  createMessage: (data) => axios.post(`${API_URL}/api/messages`, data),
  sendReply: (id, content, draftId) => 
    axios.post(`${API_URL}/api/messages/${id}/send`, { content, draft_id: draftId }),
  regenerateDraft: (id) => axios.post(`${API_URL}/api/messages/${id}/regenerate`),
  archiveMessage: (id) => axios.post(`${API_URL}/api/messages/${id}/archive`),
  
  // Stats
  getStats: () => axios.get(`${API_URL}/api/stats`),
  getRecentLearning: () => axios.get(`${API_URL}/api/learning/recent`),
};
```

### Task 3.5: 建立 frontend/src/hooks/useMessages.js
```javascript
import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

export function useMessages() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMessages = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getPendingMessages();
      setMessages(res.data.messages);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMessages();
    // Polling every 10 seconds
    const interval = setInterval(fetchMessages, 10000);
    return () => clearInterval(interval);
  }, [fetchMessages]);

  return { messages, loading, error, refetch: fetchMessages };
}
```

### Task 3.6: 建立 frontend/src/components/StatsBar.jsx
```jsx
顯示：
- 待處理訊息數（紅色 badge）
- 今日已處理
- AI 採用率（綠色顯示）
```

### Task 3.7: 建立 frontend/src/components/MessageCard.jsx
```jsx
訊息卡片，包含：
- 來源 icon（LINE 綠色、Email 藍色、電話 橙色）
- 客戶名稱 + 時間
- 原始訊息（灰底區塊）
- AI 策略建議（黃色提示框）
- 草稿編輯 textarea
- 按鈕：發送、稍後處理、重新生成
```

### Task 3.8: 建立 frontend/src/components/ManualInput.jsx
```jsx
側邊欄元件：
- 來源選擇（LINE 個人、電話、其他）
- 客戶名稱輸入
- 訊息內容 textarea
- 新增按鈕
```

### Task 3.9: 建立 frontend/src/components/LearningPanel.jsx
```jsx
側邊欄元件：
- 標題：📈 學習記錄
- 顯示最近 5 筆修改原因
```

### Task 3.10: 建立 frontend/src/pages/Dashboard.jsx
```jsx
主頁面：
- Header（標題 + StatsBar）
- 左側：MessageList（待處理訊息）
- 中間：選中的 MessageCard（詳情 + 編輯）
- 右側：ManualInput + LearningPanel
```

### Task 3.11: 建立 frontend/src/App.jsx
```jsx
- React Router 設定
- / -> Dashboard
- 深色主題
```

### Task 3.12: 建立 frontend/vite.config.js
```javascript
export default {
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8787',
      '/webhook': 'http://localhost:8787',
    }
  }
}
```

---

## Phase 4: 整合測試

### Task 4.1: 建立 scripts/init_db.py
```python
初始化資料庫，建立所有表
```

### Task 4.2: 建立 scripts/seed_data.py
```python
插入測試資料：
- 3 筆待處理訊息
- 對應的草稿
```

### Task 4.3: 建立 docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8787:8787"
    env_file:
      - .env
    volumes:
      - ./brain.db:/app/brain.db

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

### Task 4.4: 建立 backend/Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8787"]
```

### Task 4.5: 建立 frontend/Dockerfile
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

---

## 完成檢查清單

- [ ] 後端可以啟動 (`uvicorn main:app --port 8787`)
- [ ] 前端可以啟動 (`npm run dev`)
- [ ] LINE Webhook 可以接收訊息
- [ ] AI 草稿可以生成
- [ ] Dashboard 可以顯示待處理訊息
- [ ] 可以編輯並發送回覆
- [ ] 修改記錄有儲存
- [ ] 手動新增訊息功能正常
- [ ] Docker 可以 build 和 run
