# OMR Checker - Serverless Web Version

<div align="center">

📝 **完全在瀏覽器端運行的答案卡辨識系統**

[![OpenCV.js](https://img.shields.io/badge/OpenCV.js-4.x-blue.svg)](https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/demo-GitHub%20Pages-brightgreen.svg)](https://your-username.github.io/OMRChecker/)

</div>

---

## 📋 專案簡介

OMR Checker Serverless Web 是一個 **100% 靜態網頁** 的答案卡辨識系統，使用 **OpenCV.js** 進行影像處理，所有運算都在瀏覽器端完成，**無需任何後端伺服器**。

### ✨ 核心特性

- ✅ **100% 靜態網頁** - 可直接開啟 HTML 或部署到 GitHub Pages
- ✅ **無伺服器依賴** - 所有處理都在瀏覽器端完成
- ✅ **離線可用** - 下載後可完全離線使用
- ✅ **跨平台** - 支援所有現代瀏覽器 (Chrome, Firefox, Safari, Edge)
- ✅ **隱私保護** - 影像資料不會上傳到任何伺服器
- ✅ **批次處理** - 支援一次處理多張答案卡
- ✅ **資料匯出** - 支援 CSV 和 JSON 格式匯出

---

## 🚀 快速開始

### 方法 1: 直接開啟 (最簡單)

1. 下載或克隆本專案
2. 直接雙擊開啟 `index.html`
3. 等待 OpenCV.js 載入完成即可使用

### 方法 2: 使用本地 HTTP 伺服器 (推薦)

```bash
# Python 3
cd serverless_web
python3 -m http.server 8000

# Node.js
npx serve

# 然後訪問 http://localhost:8000
```

### 方法 3: 部署到 GitHub Pages (推薦用於分享)

#### 快速部署步驟

```bash
# 1. Fork 或 Clone 本專案
git clone https://github.com/your-username/OMRChecker.git
cd OMRChecker

# 2. 切換到 serverless_web 分支（如果存在）
git checkout serverless_web

# 3. 推送到你的 GitHub 倉庫
git remote set-url origin https://github.com/你的帳號/OMRChecker.git
git push -u origin serverless_web
```

#### 啟用 GitHub Pages

1. 前往 GitHub 倉庫的 **Settings** 頁面
2. 點選左側選單的 **Pages**
3. 在 **Source** 區域:
   - Branch: 選擇 `serverless_web`
   - Folder: 選擇 `/root` 或 `/serverless_web` (視專案結構而定)
4. 點擊 **Save**
5. 等待 1-2 分鐘，訪問 `https://你的帳號.github.io/OMRChecker/`

📖 **詳細部署步驟請參考**: [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📸 功能展示

> **注意**: 部署到 GitHub Pages 後，建議在此處添加實際的功能截圖。

### 主要介面

- **系統初始化**: 顯示 OpenCV.js 載入進度
- **檔案上傳**: 支援拖放與批次選擇
- **影像處理**: 即時顯示處理步驟（灰階、降噪、二值化、透視校正）
- **答案檢測**: 視覺化標記檢測結果
- **批次處理**: 進度追蹤與結果彙整
- **結果匯出**: CSV/JSON 格式下載

### 如何添加截圖

部署完成後，建議添加以下截圖：

1. 在 `serverless_web/` 目錄下建立 `screenshots/` 資料夾
2. 擷取主要功能畫面並儲存為 PNG 格式
3. 更新 README.md，插入圖片連結：
   ```markdown
   ![主介面](screenshots/main-interface.png)
   ![處理結果](screenshots/processing-result.png)
   ```

---

## 💡 使用說明

### 單張答案卡處理

1. **上傳檔案**:
   - 上傳 OMR 答案卡圖檔 (PNG/JPG)
   - 上傳模板檔案 (`template.json`)
   - 選填：設定檔、評分標準、自訂標記圖檔

2. **點擊「開始辨識答案卡」**

3. **查看結果**:
   - 即時查看影像處理步驟（灰階、降噪、二值化、透視校正）
   - 檢視答案檢測結果（綠色=答對，紅色=答錯，灰色=未填塗）

4. **匯出結果**:
   - 📊 **CSV**: 適合在 Excel/Google Sheets 中分析
   - 📄 **JSON**: 適合與其他系統整合

### 批次處理（多張答案卡）

1. **上傳多張圖檔**: 選擇多個答案卡圖檔
2. **上傳模板**: 必須提供 `template.json`
3. **選填設定**: Config、Evaluation、自訂 Marker
4. **處理選項**:
   - ✅ 啟用自動對齊（實驗功能）
   - ✅ 版面配置模式（視覺化模板配置）
5. **點擊「開始辨識答案卡」**
6. **批次完成後**:
   - 查看所有處理結果
   - 下載 CSV 或 JSON 彙整檔案

### 歷史記錄管理

- 點擊「查看歷史記錄」查看過往處理結果
- 支援刪除單筆或全部記錄
- 批次匯出歷史記錄為 CSV/JSON

### 詳細文件

- 📖 [完整使用者指南](docs/USER_GUIDE.md)
- 📋 [範例檔案說明](samples/README.md)
- 🧪 [測試說明](tests/test-export.html)
- 🚀 [部署指南](DEPLOYMENT.md)

---

## 📁 專案結構

```
serverless_web/
├── index.html                     # 主頁面（含批次處理 UI）
├── .nojekyll                      # GitHub Pages 配置
├── favicon.svg                    # 網站圖示
├── assets/
│   ├── css/
│   │   └── style.css             # 樣式表（響應式設計 + 動畫）
│   ├── js/
│   │   ├── app.js                # 主應用程式（含批次處理邏輯）
│   │   ├── batch-processor.js    # 批次處理核心模組
│   │   ├── config-parser.js      # 設定檔解析器
│   │   ├── opencv-loader.js      # OpenCV.js 載入器
│   │   ├── image-processor.js    # 影像處理模組
│   │   ├── storage.js            # IndexedDB 儲存模組
│   │   └── export.js             # CSV/JSON 匯出模組
│   └── lib/
│       └── opencv.js             # OpenCV.js（CDN 載入）
├── workers/
│   └── image-worker.js           # Web Worker（影像處理）
├── templates/
│   └── default-template.json     # 預設 OMR 模板
├── docs/
│   └── USER_GUIDE.md             # 完整使用者指南
├── samples/
│   ├── README.md                 # 範例檔案說明
│   ├── sample-template.json      # 範例模板
│   └── sample-config.json        # 範例設定
├── tests/
│   ├── test-export.html          # 匯出功能測試
│   └── TESTING_NOTES.md          # 測試說明
├── README.md                      # 本文件
├── DEPLOYMENT.md                  # 部署指南
└── TECHNICAL_DOCUMENTATION.md     # 技術文件
```

---

## 🛠 技術棧

| 技術 | 用途 | 版本 |
|------|------|------|
| **Vanilla JavaScript** | 核心邏輯 | ES6+ |
| **OpenCV.js (WASM)** | 影像處理 | 4.x |
| **HTML5 Canvas** | 影像渲染 | - |
| **Web Workers** | 並行處理 | - |
| **IndexedDB** | 本地資料儲存 | - |
| **GitHub Pages** | 靜態網站託管 | - |

### 核心功能模組

- **批次處理引擎**: 支援多檔案並行處理
- **設定檔解析器**: 彈性解析 Template、Config、Evaluation
- **匯出引擎**: CSV/JSON 格式轉換與下載
- **儲存系統**: IndexedDB 持久化儲存

---

## 📊 功能完成度

### ✅ 已完成功能

**核心功能**
- [x] 單張答案卡辨識
- [x] 批次處理（多張答案卡）
- [x] 自動透視校正
- [x] 答案標記檢測與評分
- [x] CSV/JSON 匯出
- [x] 歷史記錄管理

**進階功能**
- [x] Web Worker 並行處理
- [x] IndexedDB 本地儲存
- [x] 自動標記生成（同心圓）
- [x] 自訂標記圖檔上傳
- [x] 配置檔解析（Template、Config、Evaluation）

**使用者體驗**
- [x] 響應式 UI 設計
- [x] 即時進度顯示
- [x] Toast 通知系統
- [x] 拖放上傳
- [x] 多語言介面（繁體中文）

---

## 📱 瀏覽器支援

| 瀏覽器 | 最低版本 | 支援狀況 |
|--------|---------|---------|
| Chrome | 67+ | ✅ 完全支援 |
| Firefox | 79+ | ✅ 完全支援 |
| Safari | 14+ | ✅ 完全支援 |
| Edge | 79+ | ✅ 完全支援 |
| IE | - | ❌ 不支援 |

### 必要功能

- WebAssembly
- Web Workers (未來)
- IndexedDB (未來)
- Canvas API

---

## 🧪 測試與驗證

### 基本功能測試

1. **系統初始化測試**:
   - 開啟 `index.html`
   - 確認 OpenCV.js 載入成功（顯示「系統就緒」）
   - 確認無 Console 錯誤

2. **單張答案卡測試**:
   - 上傳範例圖檔（參考 `samples/` 目錄）
   - 上傳 `template.json`
   - 點擊「開始辨識答案卡」
   - 確認所有處理步驟正常顯示
   - 確認評分結果正確

3. **批次處理測試**:
   - 上傳多張圖檔
   - 確認進度條正常更新
   - 確認所有檔案處理完成
   - 下載 CSV/JSON 並檢查格式

4. **匯出功能測試**:
   - 單筆結果匯出 CSV/JSON
   - 批次匯出歷史記錄
   - 使用 Excel/文字編輯器驗證檔案內容

### 瀏覽器相容性測試

| 測試項目 | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| OpenCV.js 載入 | ✅ | ✅ | ✅ | ✅ |
| 影像處理 | ✅ | ✅ | ✅ | ✅ |
| Web Worker | ✅ | ✅ | ✅ | ✅ |
| IndexedDB | ✅ | ✅ | ✅ | ✅ |
| 檔案匯出 | ✅ | ✅ | ✅ | ✅ |

### 手動測試指令

```javascript
// 在瀏覽器 Console (F12) 中執行

// 1. 檢查 OpenCV 版本
cv.getBuildInformation()

// 2. 測試矩陣建立
let mat = new cv.Mat(100, 100, cv.CV_8UC3);
console.log(`Matrix size: ${mat.rows}x${mat.cols}`);
mat.delete();

// 3. 測試 Worker 狀態
// 應該在 Console 看到 "✅ Web Worker 已成功初始化！"
```

---

## 📚 文件與資源

### 專案文件

- 📖 [使用者指南](docs/USER_GUIDE.md) - 完整的功能說明與操作指引
- 🚀 [部署指南](DEPLOYMENT.md) - GitHub Pages 部署步驟
- 🔧 [技術文件](TECHNICAL_DOCUMENTATION.md) - 架構設計與 API 說明
- 📋 [範例檔案](samples/README.md) - Template 與 Config 範例

### 測試文件

- 🧪 [測試指南](TEST_GUIDE.md) - 完整測試流程
- 📊 [匯出測試](tests/test-export.html) - CSV/JSON 匯出功能測試

### 外部資源

- [OpenCV.js 官方文件](https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html)
- [OMRChecker 原始專案](https://github.com/Udayraj123/OMRChecker)

---

## 🔒 隱私與安全

- ✅ **完全本地處理** - 所有影像處理都在本機瀏覽器完成
- ✅ **不上傳資料** - 不會將任何資料傳送到伺服器
- ✅ **離線可用** - 下載後可完全離線使用
- ⚠️ **資料儲存** - 使用瀏覽器 IndexedDB 儲存結果,清除瀏覽器資料會刪除所有記錄

---

## 🤝 貢獻

本專案歡迎貢獻！請參考以下步驟：

1. Fork 本專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

---

## 📜 授權

本專案採用 MIT License - 詳見 [LICENSE](LICENSE) 檔案。

---

## 🙏 致謝

- [OMRChecker](https://github.com/Udayraj123/OMRChecker) - 原始 Python 專案
- [OpenCV.js](https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html) - 強大的瀏覽器端電腦視覺庫

---

## 🔄 版本歷史

### v1.0.0 (2025-10-07)
- ✅ 完整的批次處理功能
- ✅ CSV/JSON 匯出支援
- ✅ IndexedDB 本地儲存
- ✅ Web Worker 並行處理
- ✅ 完整的文檔與部署指南

### v0.9.0 (2025-10-05)
- ✅ 基礎 OMR 辨識功能
- ✅ 透視校正
- ✅ 答案檢測與評分
- ✅ 響應式 UI 設計

---

<div align="center">

**建立日期**: 2025-10-05 | **最後更新**: 2025-10-07

Made with ❤️ using OpenCV.js

</div>
