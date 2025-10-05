# Stage 3 記憶體洩漏修復測試指引

## 測試目標
驗證記憶體洩漏修復是否成功，確保 OpenCV.js 的 Mat 物件正確釋放。

## 修復內容

### 1. `image-processor.js` - `correctPerspective()` 函數
**問題：** catch 區塊中雙重釋放 processedMats 追蹤的物件
**修正：**
- 將 `gray`、`blurred`、`binary`、`edges` 改為 const（由 processedMats 管理）
- 移除 catch 區塊，改用 finally 區塊清理未追蹤的資源
- 添加 `isDeleted()` 檢查避免重複釋放

### 2. `test-contour-detection.html` - 測試函數
**問題：** MatVector 清理方式錯誤
**修正：**
- `testFindContours()`: 直接使用 `cv.drawContours(visual, contours, -1, ...)` 繪製所有輪廓
- `testQuadrilateralFiltering()`: 建立臨時 MatVector 用於繪製，並在 finally 中清理

## 測試步驟

### A. 手動測試（瀏覽器）
1. 啟動測試伺服器（已在 http://localhost:8000 運行）
2. 開啟主應用：http://localhost:8000/serverless_web/index.html
3. 依序上傳以下測試影像：
   - `/samples/sample2/AdrianSample/adrian_omr.png`
   - `/samples/sample3/colored-thick-sheet/rgb-100-gsm.jpg`
   - `/samples/sample5/ScanBatch1/camscanner-1.jpg`
   - `/serverless_web/samples/test-sheet.jpg`
4. 每次上傳後檢查：
   - 透視校正是否正常完成
   - Console 無錯誤訊息
   - 角點標記正確顯示

### B. 自動測試（測試套件）
1. 開啟測試頁面：http://localhost:8000/serverless_web/tests/test-contour-detection.html
2. 點擊「執行所有測試」
3. 確認所有測試通過（綠色）
4. 檢查 Console 無記憶體相關警告

### C. 記憶體洩漏測試（Chrome DevTools）
1. 開啟 Chrome DevTools > Memory
2. 錄製 Heap Snapshot（基準）
3. 上傳並處理 10 張影像
4. 點擊「清理處理結果」按鈕
5. 強制垃圾回收（DevTools > Performance Monitor > Collect garbage）
6. 錄製第二個 Heap Snapshot
7. 比較兩個快照，確認 Mat 物件已釋放

## 預期結果
- ✅ 所有手動測試通過，無 JavaScript 錯誤
- ✅ 自動測試套件全部通過
- ✅ 記憶體快照顯示 Mat 物件正確釋放
- ✅ 長時間測試（處理 20+ 張影像）無記憶體持續增長

## 已知限制
- OpenCV.js 的記憶體管理需要手動 `delete()`，無法自動垃圾回收
- 測試環境需要支援 WebAssembly 的現代瀏覽器
- 記憶體測試需要手動操作 Chrome DevTools

## 相關檔案
- `/serverless_web/assets/js/image-processor.js` (Line 438-559)
- `/serverless_web/tests/test-contour-detection.html` (Line 396-474)
