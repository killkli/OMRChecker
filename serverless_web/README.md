# OMR Checker - Serverless Web Version

<div align="center">

📝 **完全在瀏覽器端運行的答案卡辨識系統**

[![OpenCV.js](https://img.shields.io/badge/OpenCV.js-4.x-blue.svg)](https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## 📋 專案簡介

OMR Checker Serverless Web 是一個 **100% 靜態網頁** 的答案卡辨識系統,使用 **OpenCV.js** 進行影像處理,所有運算都在瀏覽器端完成,**無需任何後端伺服器**。

### ✨ 核心特性

- ✅ **100% 靜態網頁** - 可直接開啟 HTML 或部署到 GitHub Pages
- ✅ **無伺服器依賴** - 所有處理都在瀏覽器端完成
- ✅ **離線可用** - 下載後可完全離線使用
- ✅ **跨平台** - 支援所有現代瀏覽器 (Chrome, Firefox, Safari, Edge)
- ✅ **隱私保護** - 影像資料不會上傳到任何伺服器

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

### 方法 3: 部署到 GitHub Pages

```bash
# 1. 建立 GitHub 倉庫並推送程式碼
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的帳號/omr-checker.git
git push -u origin main

# 2. 到 Settings > Pages > Source > 選擇 main branch
# 3. 訪問 https://你的帳號.github.io/omr-checker/
```

---

## 📁 專案結構

```
serverless_web/
├── index.html                 # 主頁面
├── assets/
│   ├── css/
│   │   └── style.css         # 樣式表 (響應式設計)
│   ├── js/
│   │   ├── app.js            # 主應用程式
│   │   └── opencv-loader.js  # OpenCV.js 載入器
│   └── lib/
│       └── [預留 opencv.js 位置]
├── workers/
│   └── [預留 Web Worker 位置]
├── templates/
│   └── [預留 OMR 模板位置]
├── README.md                  # 本文件
└── TECHNICAL_DOCUMENTATION.md # 技術文件
```

---

## 🛠 技術棧

| 技術 | 用途 | 版本 |
|------|------|------|
| **Vanilla JavaScript** | 核心邏輯 | ES6+ |
| **OpenCV.js (WASM)** | 影像處理 | 4.x |
| **HTML5 Canvas** | 影像渲染 | - |
| **IndexedDB** | 資料儲存 (未來) | - |
| **Web Workers** | 並行處理 (未來) | - |

---

## 📊 目前進度 (Stage 1)

### ✅ 已完成功能

- [x] 專案目錄結構建立
- [x] HTML 主頁面實作
- [x] OpenCV.js 載入器實作
- [x] 載入進度視覺化
- [x] 基本 UI 設計 (響應式)
- [x] 錯誤處理機制

### 🔄 開發中

- [ ] 影像上傳功能 (Stage 2)
- [ ] 影像預處理 (Stage 2)
- [ ] 輪廓檢測與透視校正 (Stage 3)
- [ ] 答案標記辨識 (Stage 4)

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

## 🧪 測試步驟

### Stage 1 測試標準

1. 用瀏覽器開啟 `index.html`
2. 應該看到「正在載入 OpenCV.js...」訊息
3. 載入完成後顯示「OpenCV.js 已就緒」
4. 打開瀏覽器 Console (F12),應該可以看到:
   - ✅ OpenCV.js 載入完成
   - ✅ OpenCV 版本資訊
   - ✅ 功能測試通過
5. 無任何 JavaScript 錯誤

### 手動測試

```bash
# 在 Console 中執行以下指令測試 OpenCV
cv.getBuildInformation()  # 應顯示版本資訊

# 測試矩陣建立
let mat = new cv.Mat(100, 100, cv.CV_8UC3);
console.log(mat.rows, mat.cols);  # 應輸出 100 100
mat.delete();  # 記得釋放記憶體
```

---

## 📚 相關文件

- **實施計劃**: `IMPLEMENTATION_PLAN.md` (專案根目錄)
- **技術文件**: `TECHNICAL_DOCUMENTATION.md`
- **OpenCV.js 官方文件**: https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html

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

<div align="center">

**建立日期**: 2025-10-05 | **最後更新**: 2025-10-05

</div>
