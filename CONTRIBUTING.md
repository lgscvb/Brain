# 貢獻指南

感謝您對 Brain AI 客服系統的關注！我們歡迎所有形式的貢獻。

## 📋 如何貢獻

### 回報問題 (Issues)

如果您發現 bug 或有功能建議，請：

1. 搜尋現有 Issues，確認問題未被回報
2. 建立新 Issue，使用清楚的標題和描述
3. 提供重現步驟、預期行為和實際行為
4. 附上相關的錯誤訊息、截圖或日誌

### 提交程式碼 (Pull Requests)

#### 開發流程

1. **Fork 專案**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Brain.git
   cd Brain
   ```

2. **建立分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **進行開發**
   - 遵循現有的程式碼風格
   - 新增必要的測試
   - 確保所有測試通過
   - 更新相關文件

4. **提交變更**
   ```bash
   git add .
   git commit -m "feat: 新增某某功能"
   # 使用語義化提交訊息
   ```

5. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **建立 Pull Request**
   - 填寫清楚的 PR 描述
   - 說明變更的動機和影響
   - 連結相關的 Issues

#### Commit 訊息格式

使用 [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` 新功能
- `fix:` Bug 修復
- `docs:` 文件更新
- `style:` 程式碼格式調整
- `refactor:` 重構
- `test:` 測試相關
- `chore:` 建構或輔助工具變更

範例：
```
feat: 新增客戶情緒分析功能
fix: 修復 LINE Webhook 連線逾時問題
docs: 更新部署指南說明
```

## 🛠 開發環境設定

### 後端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 前端

```bash
cd frontend
npm install
```

## ✅ 測試

### 後端測試

```bash
cd backend
pytest
```

### 前端測試

```bash
cd frontend
npm run test
```

## 📖 程式碼風格

### Python
- 遵循 PEP 8
- 使用 type hints
- Docstring 使用 Google 風格

### JavaScript/React
- 使用 ES6+ 語法
- 函數元件優先於類別元件
- 使用 hooks 管理狀態

## 🎯 優先開發項目

請參考 [task.md](https://github.com/lgscvb/Brain/blob/main/.gemini/antigravity/brain/task.md) 中的「未來優化方向」。

目前優先級：
1. 監控與通知系統
2. 進階 AI 功能
3. 數據分析儀表板
4. 安全強化

## 💬 聯絡

有任何問題歡迎：
- 建立 Issue
- 透過 Discussions 討論

---

再次感謝您的貢獻！🙏
