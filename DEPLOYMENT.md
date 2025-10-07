# OMR Checker Serverless - 部署指南

本指南提供詳細的步驟，協助你將 OMR Checker Serverless Web 應用程式部署到 GitHub Pages。

---

## 📋 目錄

- [前置需求](#前置需求)
- [方法 1: 部署到 GitHub Pages](#方法-1-部署到-github-pages)
- [方法 2: 部署到其他靜態網站託管服務](#方法-2-部署到其他靜態網站託管服務)
- [常見問題排解](#常見問題排解)
- [進階配置](#進階配置)

---

## 前置需求

在開始之前，請確認你已準備以下項目：

- ✅ **GitHub 帳號**（用於 GitHub Pages）
- ✅ **Git 已安裝**（版本 2.x 以上）
- ✅ **瀏覽器**（Chrome、Firefox、Safari 或 Edge）
- ✅ **（選填）GitHub CLI** - 用於快速操作

### 檢查 Git 版本

```bash
git --version
# 應顯示 git version 2.x.x 或更高
```

---

## 方法 1: 部署到 GitHub Pages

GitHub Pages 是最推薦的部署方式，完全免費且設定簡單。

### 步驟 1: 準備 GitHub 倉庫

#### 選項 A: Fork 現有專案（推薦給一般使用者）

1. 前往原始專案頁面: `https://github.com/原作者/OMRChecker`
2. 點擊右上角的 **Fork** 按鈕
3. 選擇你的帳號作為 Fork 目的地
4. 等待 Fork 完成

#### 選項 B: 從零開始（推薦給開發者）

```bash
# 1. Clone 專案到本機
git clone https://github.com/你的帳號/OMRChecker.git
cd OMRChecker

# 2. 切換到 serverless_web 分支（如果存在）
git checkout serverless_web

# 或創建新分支
git checkout -b serverless_web
```

---

### 步驟 2: 驗證專案檔案

確認以下必要檔案存在於 `serverless_web/` 目錄中：

```bash
# 檢查目錄結構
ls -la serverless_web/

# 必要檔案清單：
# ✅ index.html
# ✅ .nojekyll (重要！GitHub Pages 配置)
# ✅ favicon.svg
# ✅ assets/（包含 css, js, lib）
# ✅ workers/image-worker.js
# ✅ templates/default-template.json
```

#### 為什麼需要 `.nojekyll`？

GitHub Pages 預設使用 Jekyll 處理靜態檔案，但我們的專案不需要 Jekyll。`.nojekyll` 檔案告訴 GitHub Pages 跳過 Jekyll 處理，直接部署原始檔案。

如果 `.nojekyll` 不存在，請建立它：

```bash
cd serverless_web
touch .nojekyll
git add .nojekyll
git commit -m "Add .nojekyll for GitHub Pages"
```

---

### 步驟 3: 推送程式碼到 GitHub

```bash
# 1. 添加所有變更
git add .

# 2. 提交變更
git commit -m "Prepare for GitHub Pages deployment"

# 3. 推送到 GitHub（第一次推送）
git push -u origin serverless_web

# 之後的推送只需要
git push
```

---

### 步驟 4: 啟用 GitHub Pages

#### 使用 GitHub 網頁介面

1. 前往你的 GitHub 倉庫頁面
2. 點擊 **Settings**（設定）
3. 在左側選單中找到 **Pages**
4. 在 **Source** 區域:
   - **Branch**: 選擇 `serverless_web`
   - **Folder**: 選擇 `/ (root)` 或 `/serverless_web`（視專案結構而定）
5. 點擊 **Save**

#### 使用 GitHub CLI（進階）

```bash
# 安裝 GitHub CLI (如果尚未安裝)
# macOS: brew install gh
# Windows: choco install gh
# Linux: 參考 https://cli.github.com/

# 啟用 GitHub Pages
gh repo edit --enable-pages --pages-branch serverless_web --pages-path /
```

---

### 步驟 5: 驗證部署

1. 等待 1-2 分鐘，讓 GitHub Pages 建置完成
2. 前往 GitHub 倉庫的 **Settings > Pages**
3. 你會看到部署成功的訊息，例如：
   ```
   ✅ Your site is live at https://你的帳號.github.io/OMRChecker/
   ```
4. 點擊連結測試網站

#### 檢查部署狀態

```bash
# 使用 GitHub CLI 檢查部署狀態
gh run list --workflow=pages-build-deployment
```

---

### 步驟 6: 測試部署的網站

開啟部署的 URL，執行以下測試：

1. ✅ 確認頁面正常載入
2. ✅ OpenCV.js 初始化成功（顯示「系統就緒」）
3. ✅ 上傳功能正常
4. ✅ 影像處理功能正常
5. ✅ 批次處理功能正常
6. ✅ CSV/JSON 匯出正常
7. ✅ 無 Console 錯誤（按 F12 檢查）

---

## 方法 2: 部署到其他靜態網站託管服務

OMR Checker Serverless 是純靜態網站，可部署到任何支援靜態網站的服務。

### Netlify 部署

1. 註冊 [Netlify](https://www.netlify.com/)
2. 點擊 **New site from Git**
3. 連接你的 GitHub 倉庫
4. 設定:
   - **Branch to deploy**: `serverless_web`
   - **Base directory**: `serverless_web/`
   - **Build command**: （留空）
   - **Publish directory**: `.`（目前目錄）
5. 點擊 **Deploy site**

### Vercel 部署

1. 註冊 [Vercel](https://vercel.com/)
2. 點擊 **New Project**
3. 導入你的 GitHub 倉庫
4. 設定:
   - **Framework Preset**: Other
   - **Root Directory**: `serverless_web`
   - **Build Command**: （留空）
   - **Output Directory**: `.`
5. 點擊 **Deploy**

### Cloudflare Pages 部署

1. 註冊 [Cloudflare Pages](https://pages.cloudflare.com/)
2. 連接你的 GitHub 倉庫
3. 設定:
   - **Production branch**: `serverless_web`
   - **Build command**: （留空）
   - **Build output directory**: `serverless_web`
4. 點擊 **Save and Deploy**

---

## 常見問題排解

### 問題 1: 頁面顯示 404 錯誤

**可能原因**:
- GitHub Pages 尚未完成建置
- 分支或目錄設定錯誤
- `.nojekyll` 檔案遺失

**解決方案**:
```bash
# 1. 確認 .nojekyll 存在
ls -la serverless_web/.nojekyll

# 2. 如果不存在，建立它
cd serverless_web
touch .nojekyll
git add .nojekyll
git commit -m "Add .nojekyll"
git push

# 3. 檢查 GitHub Pages 設定
# 前往 Settings > Pages，確認分支和目錄正確
```

---

### 問題 2: OpenCV.js 載入失敗

**可能原因**:
- CDN 被封鎖
- 路徑設定錯誤
- CORS 問題

**解決方案**:
1. 檢查 `assets/js/opencv-loader.js` 中的 OpenCV.js 路徑
2. 確認路徑使用相對路徑（`./assets/lib/opencv.js`）而非絕對路徑
3. 檢查 Console 是否有 CORS 錯誤

---

### 問題 3: 資源檔案載入失敗（404）

**可能原因**:
- 路徑使用絕對路徑（如 `/assets/...`）
- 在 GitHub Pages 子目錄部署時路徑錯誤

**解決方案**:
```bash
# 檢查所有路徑是否使用相對路徑
grep -r "src=\"/" serverless_web/*.html
grep -r "href=\"/" serverless_web/*.html

# 正確範例：
# ✅ <link href="./assets/css/style.css">
# ❌ <link href="/assets/css/style.css">
```

---

### 問題 4: Web Worker 無法載入

**可能原因**:
- Worker 路徑錯誤
- CORS 限制

**解決方案**:
1. 確認 `workers/image-worker.js` 存在
2. 檢查 `app.js` 中 Worker 路徑使用相對路徑：
   ```javascript
   this.worker = new Worker('./workers/image-worker.js');
   ```

---

## 進階配置

### 自訂網域設定

如果你有自己的網域，可以設定 GitHub Pages 使用自訂網域：

1. 前往 **Settings > Pages**
2. 在 **Custom domain** 欄位輸入你的網域（例如：`omr.example.com`）
3. 點擊 **Save**
4. 在你的 DNS 設定中，新增以下記錄：
   ```
   Type: CNAME
   Name: omr (或 www)
   Value: 你的帳號.github.io
   ```

### HTTPS 強制啟用

GitHub Pages 自動提供免費的 HTTPS，建議啟用：

1. 前往 **Settings > Pages**
2. 勾選 **Enforce HTTPS**

### 效能優化

1. **啟用瀏覽器快取**: GitHub Pages 自動設定適當的快取標頭
2. **壓縮資源**: 考慮使用工具壓縮 CSS 和 JS（選填）
3. **圖片最佳化**: 使用適當的圖片格式和大小

---

## 更新部署

當你修改程式碼後，重新部署非常簡單：

```bash
# 1. 提交變更
git add .
git commit -m "Update feature X"

# 2. 推送到 GitHub
git push

# 3. GitHub Pages 會自動重新建置（通常 1-2 分鐘）
```

---

## 檢查清單

部署前，請確認：

- [ ] `.nojekyll` 檔案存在
- [ ] 所有資源路徑使用相對路徑（`./`）
- [ ] `favicon.svg` 存在
- [ ] `templates/default-template.json` 存在
- [ ] 所有必要的 JavaScript 檔案存在
- [ ] 已測試本地執行正常（`python3 -m http.server`）
- [ ] 已推送所有變更到 GitHub
- [ ] GitHub Pages 設定正確

---

## 需要協助？

如果遇到問題，請參考：

- 📖 [README.md](README.md) - 專案說明
- 🧪 [TEST_GUIDE.md](TEST_GUIDE.md) - 測試指南
- 🔧 [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md) - 技術文件
- 💬 [GitHub Issues](https://github.com/你的帳號/OMRChecker/issues) - 提出問題

---

<div align="center">

**祝部署順利！** 🚀

如有任何問題，歡迎開啟 Issue 討論。

</div>
