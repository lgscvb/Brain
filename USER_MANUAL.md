# 📘 Brain AI 客服系統 - 使用者操作手冊

## 目錄
1. [系統登入](#1-系統登入)
2. [初始設定](#2-初始設定)
3. [訊息管理](#3-訊息管理)
4. [自動回覆模式](#4-自動回覆模式)
5. [系統日誌](#5-系統日誌)
6. [常見問題排除](#6-常見問題排除)

---

## 1. 系統登入

### 訪問網址
```
https://brain.yourspce.org
```

### 介面說明
進入系統後，您會看到五個主要頁籤：
- 📊 **儀表板** - 系統統計總覽
- 💬 **訊息管理** - 處理客戶訊息
- 📋 **系統日誌** - 查看系統運行記錄
- ⚙️ **系統設定** - 配置 API Keys 和模式
- 📖 **使用說明** - 快速參考指南

---

## 2. 初始設定

### 步驟 1：設定 API Keys

1. 點擊頁面上方的 **「系統設定」**
2. 在「Claude API」區塊填入：
   ```
   Anthropic API Key: sk-ant-api03-...
   ```
3. 在「LINE Messaging API」區塊填入：
   ```
   Channel Access Token: eyJh...
   Channel Secret: 1b2c3d4e...
   ```
4. 點擊 **「儲存設定」**
5. 系統會提示「請重新啟動伺服器以套用新設定」

### 步驟 2：重啟後端服務

在伺服器上執行：
```bash
docker compose restart backend
```

### 步驟 3：配置 LINE Webhook

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 選擇您的 Messaging API Channel
3. 在「Webhook settings」填入：
   ```
   https://brain.yourspce.org/webhook/line
   ```
4. 啟用「Use webhook」
5. 測試 Webhook（應顯示成功）

✅ **設定完成！** 現在您可以開始接收並處理訊息了。

---

## 3. 訊息管理

### 查看待處理訊息

1. 點擊 **「訊息管理」**
2. 您會看到所有收到的訊息列表，包含：
   - **來源**：訊息來自哪個平台（LINE OA）
   - **發送者**：客戶名稱
   - **內容**：客戶的訊息
   - **狀態**：pending（待處理）/ processing（處理中）/ sent（已發送）
   - **優先度**：low / medium / high

### 生成 AI 草稿

1. 找到您想回覆的訊息
2. 點擊 **「生成草稿」** 按鈕
3. 系統會使用 Claude AI 分析訊息並生成多個回覆草稿
4. 等待約 5-10 秒，草稿會自動顯示在訊息下方

### 查看草稿內容

草稿會顯示以下資訊：
- **策略**：AI 使用的回覆策略（如「提出問題了解需求」）
- **意圖分析**：客戶的可能意圖
- **回覆內容**：建議的回覆文字

### 發送回覆

1. 選擇您滿意的草稿
2. 如需修改，直接點擊草稿內容編輯
3. 點擊 **「發送」** 按鈕
4. 訊息會立即發送到客戶的 LINE

### 篩選訊息

使用頁面上方的篩選器：
- **來源**：選擇 LINE OA
- **狀態**：pending / sent / all
- **優先度**：low / medium / high

---

## 4. 自動回覆模式

### 使用場景

**手動模式**（預設）：
- ✅ 需要精準控制回覆內容
- ✅ 上班時間且有人力審核
- ✅ 處理重要客戶或複雜問題

**自動模式**：
- ✅ 半夜 23:00-08:00 無人值班
- ✅ 忙碌時段人手不足
- ✅ 簡單問題快速回應

### 開啟自動回覆

1. 前往 **「系統設定」**
2. 找到 **「自動回覆模式」** 區塊
3. 點擊切換開關變為 **「開啟」**（綠色）
4. 點擊 **「儲存設定」**
5. 重啟後端服務

### 自動模式運作方式

1. 客戶傳送訊息到 LINE
2. Brain 接收訊息
3. AI 自動生成草稿
4. **直接發送第一個草稿**（不需人工審核）
5. 訊息狀態更新為「已發送」

### 關閉自動回覆

1. 前往 **「系統設定」**
2. 將 **「自動回覆模式」** 切換為 **「關閉」**
3. 儲存並重啟後端

---

## 5. 系統日誌

### 查看日誌

1. 點擊 **「系統日誌」**
2. 選擇日誌類型：
   - **主要日誌**：所有系統活動
   - **錯誤日誌**：只顯示錯誤

### 篩選日誌

- **等級**：DEBUG / INFO / WARNING / ERROR
- **搜尋**：輸入關鍵字過濾

### 自動更新

日誌會每 5 秒自動更新，顯示最新的系統活動。

### 清空日誌

1. 點擊 **「清空日誌」** 按鈕
2. 選擇要清空的日誌類型
3. 確認操作

⚠️ **注意**：清空後無法恢復，請謹慎操作！

---

## 6. 常見問題排除

### ❌ LINE 收不到訊息

**檢查項目**：
1. Webhook URL 是否正確？
2. Webhook 是否已啟用？
3. 在「系統日誌」中搜尋「webhook」，確認是否有收到事件
4. 確認 LINE Channel Secret 正確

**解決方法**：
```bash
# 測試 Webhook
curl -X POST https://brain.yourspce.org/webhook/line \
  -H "Content-Type: application/json" \
  -d '{"events":[]}'
```

### ❌ AI 草稿生成失敗

**可能原因**：
1. Claude API Key 無效或額度用盡
2. API 請求逾時
3. 網路連線問題

**檢查方法**：
1. 前往「系統日誌」
2. 篩選 ERROR 等級
3. 查看錯誤訊息

### ❌ 設定儲存後沒有生效

**解決方法**：
```bash
# 登入伺服器
ssh your-vm

# 重啟後端
cd ~/Brain
docker compose restart backend

# 確認容器運行
docker compose ps
```

### ❌ 自動模式沒有自動發送

**檢查項目**：
1. 在「系統設定」確認開關已開啟
2. 確認已儲存設定並重啟
3. 在「系統日誌」搜尋「自動模式」

### ❌ 資料庫錯誤

**解決方法**：
```bash
# 備份資料庫
cp data/brain.db data/brain.db.backup

# 重建資料庫
rm data/brain.db
docker compose restart backend
```

⚠️ **注意**：重建資料庫會清空所有資料！

---

## 📞 技術支援

如遇到無法解決的問題，請聯絡技術團隊：

- **Email**：support@hourjungle.com
- **GitHub Issues**：https://github.com/lgscvb/Brain/issues

---

## 📚 延伸閱讀

- [README.md](README.md) - 完整技術文件
- [API 文件](https://brain.yourspce.org/api/docs) - API 參考
- [PR Description](PR_DESCRIPTION.md) - 版本發布說明

---

**更新時間**：2025-12-02  
**版本**：v1.0
