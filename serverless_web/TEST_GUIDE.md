# Stage 1 測試指南

## 📋 測試目標

驗證 OpenCV.js 載入機制和基礎 UI 功能是否正常運作。

---

## 🧪 測試步驟

### 方法 1: 直接開啟 HTML

1. **開啟檔案**
   ```bash
   # macOS
   open serverless_web/index.html

   # Linux
   xdg-open serverless_web/index.html

   # Windows
   start serverless_web/index.html
   ```

2. **觀察載入過程**
   - 應該看到「正在載入 OpenCV.js...」訊息
   - 進度條應該從 0% 逐漸增加
   - 狀態文字會更新 (「正在下載...」→「載入完成！」)

3. **驗證載入成功**
   - ✅ 狀態圖示變為綠色勾號 (✅)
   - ✅ 顯示「OpenCV.js 已就緒」
   - ✅ 下方出現「OpenCV 版本資訊」卡片
   - ✅ 頁面底部顯示「影像上傳功能將在 Stage 2 實作」

### 方法 2: 使用 HTTP 伺服器 (推薦)

1. **啟動伺服器**
   ```bash
   cd serverless_web

   # Python 3
   python3 -m http.server 8000

   # 或 Node.js
   npx serve
   ```

2. **開啟瀏覽器**
   - 訪問 http://localhost:8000
   - 執行上述「觀察載入過程」的驗證步驟

---

## 🔍 瀏覽器 Console 測試

開啟瀏覽器開發者工具 (按 F12),在 Console 標籤中應該看到:

### 預期輸出

```
🚀 OMR Checker 應用程式啟動
📊 載入進度: 10%
📊 載入進度: 25%
...
📊 載入進度: 100%
✅ OpenCV.js 載入完成 (耗時: X.XX 秒)
OpenCV 版本資訊: <版本資訊字串>
✅ OpenCV.js 已就緒,開始初始化應用程式
🧪 OpenCV 功能測試:
  - 矩陣建立: ✅ (100x100)
  - 矩陣類型: 16
  - 記憶體管理: ✅
✅ OpenCV 所有功能測試通過
ℹ️ OpenCV 版本: 4.x.x
```

### 手動測試指令

在 Console 中執行以下指令來驗證 OpenCV.js 是否正常運作:

```javascript
// 1. 檢查 OpenCV 是否已載入
console.log('OpenCV 已載入:', typeof cv !== 'undefined');

// 2. 取得版本資訊
cv.getBuildInformation();

// 3. 測試建立矩陣
let testMat = new cv.Mat(100, 100, cv.CV_8UC3);
console.log('矩陣尺寸:', testMat.rows, 'x', testMat.cols);
testMat.delete();  // 記得釋放記憶體

// 4. 檢查 Loader 實例
console.log('Loader 已就緒:', window.opencvLoader.checkReady());
console.log('OpenCV 版本:', window.opencvLoader.getVersion());
```

---

## ✅ 驗收標準

### 必須通過的測試項目

- [ ] **視覺測試**
  - [ ] 頁面正確顯示標題「📝 OMR Checker」
  - [ ] 載入進度條動畫流暢
  - [ ] 載入完成後狀態卡片變為綠色邊框
  - [ ] 顯示 OpenCV 版本資訊

- [ ] **功能測試**
  - [ ] OpenCV.js 成功從 CDN 載入
  - [ ] `window.opencvLoader.checkReady()` 返回 `true`
  - [ ] 可以建立和釋放 `cv.Mat` 物件
  - [ ] 無 JavaScript 錯誤

- [ ] **響應式測試**
  - [ ] 在桌面瀏覽器 (>1200px) 正確顯示
  - [ ] 在平板 (768px-1200px) 正確顯示
  - [ ] 在手機 (<768px) 正確顯示

- [ ] **跨瀏覽器測試**
  - [ ] Chrome 67+ ✅
  - [ ] Firefox 79+ ✅
  - [ ] Safari 14+ ✅
  - [ ] Edge 79+ ✅

---

## 🐛 常見問題與解決方案

### 問題 1: 載入超時

**現象**: 超過 15 秒仍顯示「正在載入...」

**原因**:
- 網路連線問題
- CDN 不可用

**解決**:
1. 檢查網路連線
2. 重新整理頁面
3. 如果問題持續,考慮下載 opencv.js 到本地:
   ```bash
   wget https://docs.opencv.org/4.x/opencv.js -O serverless_web/assets/lib/opencv.js
   ```
   然後修改 `index.html`:
   ```html
   <!-- 改為 -->
   <script async src="./assets/lib/opencv.js"></script>
   ```

### 問題 2: Console 顯示錯誤

**現象**: `Uncaught ReferenceError: cv is not defined`

**原因**: OpenCV.js 尚未載入完成就嘗試使用

**解決**:
- 確保所有 OpenCV 相關程式碼都在 `window.opencvLoader.onReady()` 回調中執行

### 問題 3: 樣式顯示異常

**現象**: 頁面看起來沒有樣式

**原因**: CSS 檔案路徑錯誤

**解決**:
1. 檢查 `assets/css/style.css` 是否存在
2. 檢查瀏覽器 Network 標籤,確認 CSS 是否成功載入

---

## 📊 效能基準

在一般的現代電腦上,預期的效能指標:

| 指標 | 預期值 |
|------|--------|
| OpenCV.js 下載時間 | < 5 秒 (快速網路) |
| 初始化時間 | < 2 秒 |
| 總載入時間 | < 7 秒 |
| 記憶體使用 | < 50 MB |
| 測試矩陣建立時間 | < 10 ms |

---

## 📝 測試檢查清單

完成測試後,請確認以下項目:

```
Stage 1 功能驗收
├── ✅ 專案結構建立完成
│   ├── index.html 存在且可開啟
│   ├── assets/css/style.css 樣式正確
│   ├── assets/js/opencv-loader.js 功能正常
│   └── assets/js/app.js 邏輯完整
│
├── ✅ OpenCV.js 載入機制
│   ├── CDN 引用正確
│   ├── 進度顯示正常
│   ├── 載入完成回調執行
│   └── 錯誤處理機制運作
│
├── ✅ UI 顯示正確
│   ├── 載入狀態視覺化
│   ├── 版本資訊顯示
│   ├── 響應式設計正常
│   └── 動畫效果流暢
│
└── ✅ 無錯誤
    ├── 無 JavaScript 錯誤
    ├── 無 CSS 載入錯誤
    └── Console 無警告訊息
```

---

## 🎯 下一步

Stage 1 測試通過後,即可進入 **Stage 2: 影像上傳與基礎處理**:

1. 實現檔案上傳 UI (拖放 + 點擊)
2. 影像讀取與驗證
3. 灰階轉換、降噪、二值化
4. Canvas 預覽功能

---

**測試完成日期**: _____________

**測試人員**: _____________

**測試結果**: ⬜ 通過 / ⬜ 失敗

**備註**:
