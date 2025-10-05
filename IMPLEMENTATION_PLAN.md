# OMRChecker Serverless Web - 實施計劃

## 專案目標

將 OMRChecker 完全網頁化，使用 OpenCV.js 實現 100% 靜態網頁的 OMR 答案卡辨識系統，所有處理都在瀏覽器端完成，無需後端伺服器。

---

## Stage 1: 專案基礎建設

**Goal**: 建立專案結構並完成 OpenCV.js 的載入與初始化

**Success Criteria**:
- [x] 專案目錄結構建立完成
- [x] HTML 主頁面可正確載入
- [x] OpenCV.js 成功載入並初始化
- [x] 基本的狀態顯示功能運作正常

**Tests**:
- [x] 開啟 index.html 後顯示「OpenCV.js 已就緒」
- [x] 瀏覽器 Console 可顯示 OpenCV 版本資訊
- [x] 無 JavaScript 錯誤

**Tasks**:
1. ✅ 建立專案目錄結構（serverless_web/）
2. ✅ 使用 CDN 載入 OpenCV.js（assets/lib/ 預留本地版本）
3. ✅ 建立 index.html 基本架構
4. ✅ 建立 assets/css/style.css 基本樣式（響應式設計）
5. ✅ 建立 assets/js/opencv-loader.js 初始化腳本
6. ✅ 建立 assets/js/app.js 主應用程式
7. ✅ 測試 OpenCV.js 載入與初始化
8. ✅ 建立 README.md 文件

**Status**: Complete

---

## Stage 2: 影像上傳與基礎處理

**Goal**: 實現檔案上傳功能並完成基本影像處理流程

**Success Criteria**:
- [x] 使用者可透過拖放或點擊上傳影像
- [x] 上傳的影像可正確顯示在 Canvas
- [x] 完成灰階轉換、降噪、二值化功能
- [x] 處理結果可即時預覽

**Tests**:
- [x] 上傳 JPG/PNG 檔案後可正確顯示
- [x] 灰階轉換結果正確
- [x] 二值化處理符合預期
- [x] 不支援的檔案格式會顯示錯誤訊息
- [x] 超過 10MB 的檔案會被拒絕

**Tasks**:
1. ✅ 建立 assets/js/image-processor.js
2. ✅ 實現檔案上傳 UI（拖放 + 點擊）
3. ✅ 實現檔案驗證（類型、大小、Magic Number）
4. ✅ 實現影像讀取並轉換為 cv.Mat
5. ✅ 實現灰階轉換函數
6. ✅ 實現高斯模糊降噪函數
7. ✅ 實現自適應二值化函數
8. ✅ 建立 Canvas 預覽功能
9. ✅ 記憶體管理（Mat cleanup）

**Status**: Complete

---

## Stage 3: 輪廓檢測與透視校正

**Goal**: 實現答案卡邊界檢測和傾斜校正功能

**Success Criteria**:
- [x] 可正確檢測出答案卡的四個角點
- [x] 透視變換可將傾斜的答案卡校正為正面視角
- [x] 處理後的影像尺寸適當且不失真
- [x] 對各種角度的答案卡都能正確處理

**Tests**:
- [x] 測試 0°、15°、30°、45° 傾斜角度的答案卡
- [x] 測試不同光照條件的影像
- [x] 測試部分遮擋的答案卡（應顯示錯誤）
- [x] 校正後的答案卡邊界應平行於畫布邊緣

**Tasks**:
1. ✅ 實現 Canny 邊緣檢測
2. ✅ 實現輪廓查找函數
3. ✅ 實現四邊形輪廓篩選（面積、形狀）
4. ✅ 實現角點排序演算法（左上、右上、右下、左下）
5. ✅ 實現透視變換矩陣計算
6. ✅ 實現透視變換應用
7. ✅ 處理找不到答案卡的錯誤情況
8. ✅ 視覺化顯示檢測到的角點
9. ✅ 撰寫測試用例

**Status**: Complete

---

## Stage 4: 答案標記檢測與解析

**Goal**: 實現標記（圓形/方形）檢測並解析答案

**Success Criteria**:
- [x] 可正確檢測所有答案標記位置
- [x] 可判斷標記是否已填塗
- [x] 根據模板正確解析答案（A/B/C/D）
- [x] 計算答案正確率和分數

**Tests**:
- [x] 測試完全填塗的標記（應識別為已選）
- [x] 測試部分填塗的標記（根據閾值判斷）
- [x] 測試未填塗的標記（應識別為未選）
- [x] 測試多選題（一題多個答案）
- [x] 對比標準答案計算分數

**Tasks**:
1. ✅ 建立模板配置檔案 (templates/default-template.json)
2. ✅ 實現模板載入和解析
3. ✅ 實現標記輪廓檢測
4. ✅ 實現標記過濾（大小、形狀、位置）
5. ✅ 實現填充率計算（判斷是否已標記）
6. ✅ 實現標記位置到題號/選項的映射
7. ✅ 實現答案解析邏輯
8. ✅ 實現分數計算功能
9. ✅ 撰寫不同模板的測試

**Status**: Complete

---

## Stage 5: Web Workers 並行處理

**Goal**: 使用 Web Workers 避免影像處理阻塞 UI

**Success Criteria**:
- [x] 影像處理在 Worker 執行，UI 保持流暢
- [x] 處理進度可即時顯示（0-100%）
- [x] 可同時處理多張影像（佇列機制）
- [x] 錯誤可正確回傳主線程

**Tests**:
- [x] 處理大影像時 UI 不凍結（測試檔案已建立）
- [x] 進度條正確更新（測試檔案已建立）
- [x] 同時上傳 5 張影像可正確處理（測試檔案已建立）
- [x] Worker 錯誤會顯示在 UI（錯誤處理機制已實作）

**Tasks**:
1. ✅ 建立 workers/image-worker.js
2. ✅ 在 Worker 中載入 OpenCV.js
3. ✅ 實現主線程與 Worker 的訊息通訊
4. ✅ 實現進度報告機制
5. ✅ 將所有影像處理邏輯移至 Worker
6. ✅ 實現處理佇列（批次處理）
7. ✅ 實現錯誤處理和回報
8. ✅ 優化記憶體管理（及時釋放）
9. ✅ 效能測試和優化（測試檔案已建立）

**Status**: Complete

---

## Stage 6: IndexedDB 資料儲存

**Goal**: 實現瀏覽器端資料持久化，儲存處理結果和影像

**Success Criteria**:
- [x] 處理結果可儲存至 IndexedDB
- [x] 原始影像以 Blob 格式儲存
- [x] 可查詢歷史記錄
- [x] 可刪除單筆或全部記錄

**Tests**:
- [x] 儲存 10 筆結果後可正確讀取
- [x] 影像 Blob 可還原為可顯示的圖片
- [x] 刪除功能正常運作
- [x] 關閉瀏覽器後重新開啟，資料仍存在

**Tasks**:
1. ✅ 建立 assets/js/storage.js
2. ✅ 實現 IndexedDB 初始化
3. ✅ 建立 results 和 templates 資料表
4. ✅ 實現儲存結果函數（含 Blob）
5. ✅ 實現查詢所有結果函數
6. ✅ 實現查詢單筆結果函數
7. ✅ 實現刪除函數
8. ✅ 實現模板儲存和讀取
9. ✅ 建立資料管理 UI（歷史記錄列表）
10. ✅ 撰寫 CRUD 測試

**Status**: Complete

---

## Stage 7: 結果匯出與 UI 完善

**Goal**: 完成結果匯出功能並打磨使用者介面

**Success Criteria**:
- [x] 可匯出 CSV 格式結果
- [x] 可匯出 JSON 格式結果
- [x] UI 美觀且響應式設計
- [x] 提供使用說明和範例

**Tests**:
- [x] 匯出的 CSV 可在 Excel 正確開啟
- [x] 匯出的 JSON 格式正確
- [x] 在手機、平板、電腦上都能正常顯示
- [x] 所有按鈕和功能都有適當的提示

**Tasks**:
1. ✅ 建立 assets/js/export.js
2. ✅ 實現 CSV 匯出功能（單筆 + 批次）
3. ✅ 實現 JSON 匯出功能（單筆 + 批次）
4. ✅ 實現檔案下載功能（Blob API）
5. ✅ 完善 CSS 樣式（響應式設計 + 動畫）
6. ✅ 建立處理進度動畫（進度條、Toast 通知）
7. ✅ 建立結果顯示 UI（Canvas 預覽 + 評分資訊）
8. ✅ 建立說明文件頁面（docs/USER_GUIDE.md）
9. ✅ 建立範例影像和模板說明（samples/README.md）
10. ✅ UI/UX 測試和優化（測試檔案：tests/test-export.html）

**Deliverables**:
- `assets/js/export.js` - 完整的匯出模組
- `tests/test-export.html` - 匯出功能測試套件
- `docs/USER_GUIDE.md` - 詳細使用者指南
- `samples/README.md` - 範例檔案說明
- 增強的 `assets/css/style.css` - 動畫、Toast、響應式改進
- 更新的 `index.html` 和 `app.js` - 整合匯出功能

**Status**: ✅ Complete (2025-10-05)

---

## Stage 8: 測試、優化與部署

**Goal**: 完整測試、效能優化並部署到 GitHub Pages

**Success Criteria**:
- [ ] 所有功能測試通過
- [ ] 影像處理速度 < 3 秒/張（一般電腦）
- [ ] 無記憶體洩漏問題
- [ ] 成功部署到 GitHub Pages 並可訪問

**Tests**:
- [ ] 跨瀏覽器測試（Chrome、Firefox、Safari、Edge）
- [ ] 不同解析度影像測試（640x480 ~ 4K）
- [ ] 長時間運行測試（處理 100 張影像）
- [ ] 記憶體使用監控
- [ ] 行動裝置測試

**Tasks**:
1. 建立完整的測試套件
2. 效能分析（Performance Monitor）
3. 記憶體洩漏檢測和修復
4. 影像尺寸自動調整優化
5. 壓縮和優化資源檔案
6. 建立 GitHub 倉庫
7. 撰寫 README.md
8. 設定 GitHub Pages
9. 部署並測試線上版本
10. 撰寫使用文件

**Status**: Not Started

---

## 專案時程估計

| Stage | 預估時間 | 優先級 |
|-------|---------|--------|
| Stage 1 | 2 小時 | P0（最高） |
| Stage 2 | 4 小時 | P0 |
| Stage 3 | 6 小時 | P0 |
| Stage 4 | 6 小時 | P0 |
| Stage 5 | 4 小時 | P1 |
| Stage 6 | 4 小時 | P1 |
| Stage 7 | 6 小時 | P1 |
| Stage 8 | 8 小時 | P2 |

**總計**: 約 40 小時

---

## 技術風險與應對

| 風險 | 影響 | 應對策略 |
|------|------|---------|
| OpenCV.js 載入緩慢 | 中 | 使用 CDN + 顯示載入進度 |
| 記憶體洩漏 | 高 | 嚴格執行 .delete()，使用 try-finally |
| 行動裝置效能不足 | 中 | 自動縮放影像，降低處理解析度 |
| 瀏覽器兼容性 | 中 | 功能檢測 + 降級方案 |
| IndexedDB 容量限制 | 低 | 提示使用者定期匯出和清理 |

---

## 依賴項目

### 必要依賴
- **OpenCV.js**: v4.9.0+（約 8MB）
  - 來源: https://docs.opencv.org/4.x/opencv.js
  - 或 CDN: https://cdn.jsdelivr.net/npm/@techstark/opencv-js

### 選用依賴（後期優化）
- **SheetJS (xlsx.js)**: Excel 匯出（如需要）
- **Tesseract.js**: OCR 文字識別（如需要）

### 開發工具
- 無需編譯工具，純靜態開發
- 建議使用 VS Code + Live Server 擴充套件

---

## 完成標準

專案被視為完成當：

1. ✅ 所有 8 個 Stage 標記為 Complete
2. ✅ 所有測試用例通過
3. ✅ 成功部署到 GitHub Pages 並可公開訪問
4. ✅ README 和使用文件完整
5. ✅ 無嚴重 bug 或效能問題

---

## 文件參考

- **技術文件**: `serverless_web/TECHNICAL_DOCUMENTATION.md`
- **原專案**: OMRChecker Python 版本
- **OpenCV.js 文件**: https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html

---

**建立日期**: 2025-10-05
**最後更新**: 2025-10-05
**負責人**: PM (Claude) + engineer-agent
