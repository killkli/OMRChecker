# OMRChecker Serverless Web - 完整功能實施計劃

## 專案目標

**打造功能完整的純前端OMR系統，100%複製Python Gradio版本的所有功能，完全靜態網頁，無需後端伺服器。**

---

## 🎯 Gradio版本功能清單（目標對照）

### 1. 📋 辨識答案卡 (Processing Tab)
- [x] 單張影像上傳處理
- [ ] **多張影像批次上傳處理**
- [x] 支援template.json載入
- [ ] 支援config.json載入
- [ ] 支援evaluation.json載入（評分標準）
- [ ] 支援自訂marker圖檔上傳
- [ ] 自動對齊選項（auto-align）
- [ ] 版面配置預覽模式（layout mode）
- [x] CSV結果匯出
- [ ] **標記後的圖片Gallery顯示**
- [ ] **詳細處理記錄顯示**

### 2. 🔧 模板建立工具 (Template Builder Tab)
- [ ] **上傳參考圖檔**
- [ ] **點擊圖片取得座標功能**
- [ ] **設定頁面尺寸（pageDimensions）**
- [ ] **設定圓圈尺寸（bubbleDimensions）**
- [ ] **新增/移除欄位區塊（fieldBlocks）**
  - [ ] 支援所有fieldType（MCQ4/5, INT, CUSTOM）
  - [ ] 設定起始座標（origin）
  - [ ] 設定欄位標籤（fieldLabels, 支援q1..10語法）
  - [ ] 設定方向（horizontal/vertical）
  - [ ] 設定間距（bubblesGap, labelsGap）
- [ ] **新增/移除自訂標籤（customLabels）**
- [ ] **新增/移除前處理器（preProcessors）**
  - [ ] CropPage
  - [ ] FeatureBasedAlignment
  - [ ] GaussianBlur
  - [ ] MedianBlur
  - [ ] Levels
  - [ ] CropOnMarkers
- [ ] **模板視覺化預覽（在參考圖上繪製所有bubble位置）**
- [ ] **匯出完整template.json**

### 3. 📄 產生空白答案卡 (Generator Tab)
- [ ] **設定題目數量（1-200）**
- [ ] **選擇題型（MCQ4/5, INT）**
- [ ] **設定欄數（橫向排列）**
- [ ] **可選QR Code（含自訂內容）**
- [ ] **3行自訂文字標題**
- [ ] **對齊標記（alignment markers）**
- [ ] **進階設定（頁面尺寸、圓圈大小）**
- [ ] **產生空白答案卡圖檔（PNG）**
- [ ] **同時產生對應的template.json**
- [ ] **下載功能（圖檔+模板）**

### 4. 📦 批次產生答案卡 (Batch Tab)
- [ ] **上傳Excel/CSV學生名單**
- [ ] **指定ID欄位名稱**
- [ ] **指定學生資料欄位（印在答案卡上）**
- [ ] **為每位學生產生專屬答案卡**
- [ ] **每張卡包含獨特的QR Code（學生ID）**
- [ ] **可印上學生個人資料（姓名、班級等）**
- [ ] **打包成ZIP檔案下載（所有圖檔+模板）**

---

## 📋 新實施計劃（9個Stage）

### Stage 1: ✅ 基礎建設（已完成）
**現狀**: 完成
- [x] OpenCV.js載入與初始化
- [x] 基本UI結構
- [x] Web Worker並行處理
- [x] IndexedDB資料儲存

---

### Stage 2: ✅ 基礎影像處理（已完成）
**現狀**: 完成
- [x] 單張影像上傳
- [x] 灰階、降噪、二值化
- [x] 透視校正
- [x] 答案檢測（支援Python fieldBlocks格式）

---

### Stage 3: ✅ 完善辨識功能（Processing Tab剩餘功能）

**Goal**: 完整實現Gradio版本的辨識答案卡功能

**Success Criteria**:
- [x] 支援多張影像批次上傳處理
- [x] 支援config.json（調整影像處理參數）
- [x] 支援evaluation.json（評分標準、答案批改）
- [x] 支援自訂marker圖檔
- [x] 標記後的圖片Gallery顯示
- [x] 詳細處理記錄（logs）顯示

**Status**: ✅ 完成 (2025-10-06)

**Tasks**:
1. [ ] 實現多檔案同時上傳UI
2. [ ] 建立config.json解析器
   - [ ] 影像處理參數（threshold, blur等）
   - [ ] 調優參數（tuning options）
3. [ ] 建立evaluation.json解析器
   - [ ] 答案鍵（answer key）
   - [ ] 評分規則（scoring rules）
   - [ ] 選項（marking scheme）
4. [ ] 實現自訂marker圖檔支持
   - [ ] 載入marker圖檔
   - [ ] 使用自訂marker進行對齊
5. [ ] 建立圖片Gallery UI組件
   - [ ] 顯示所有處理過的答案卡
   - [ ] 標記顏色（綠色正確/紅色錯誤/藍色未選正確答案）
6. [ ] 建立詳細記錄面板
   - [ ] 處理步驟記錄
   - [ ] 錯誤訊息記錄
   - [ ] 可摺疊/展開
7. [ ] 批次處理進度顯示
   - [ ] 整體進度條
   - [ ] 各個檔案處理狀態
8. [ ] 整合測試

**Deliverables**:
- `assets/js/batch-processor.js` - 批次處理邏輯
- `assets/js/config-parser.js` - config/evaluation解析器
- `assets/js/marker-handler.js` - 自訂marker處理
- `assets/css/gallery.css` - Gallery樣式
- 更新的 `index.html` - 新增Gallery和Log面板

---

### Stage 4: 🆕 模板建立工具 - 基礎框架（Template Builder - Part 1）

**Goal**: 建立互動式模板建立工具的UI框架和基本功能

**Success Criteria**:
- [ ] 可上傳參考圖檔並顯示
- [ ] 點擊圖片可取得座標
- [ ] 可設定頁面尺寸
- [ ] 可設定預設圓圈尺寸
- [ ] 基本的模板資料結構建立

**Tasks**:
1. [ ] 建立新的Tab頁面（Template Builder）
2. [ ] 實現參考圖檔上傳和顯示
3. [ ] 實現點擊座標取得功能
   - [ ] Canvas click event監聽
   - [ ] 座標計算（考慮縮放）
   - [ ] 座標顯示UI
4. [ ] 建立頁面尺寸設定UI
   - [ ] 寬度/高度輸入框
   - [ ] 即時更新
5. [ ] 建立圓圈尺寸設定UI
   - [ ] 預設寬度/高度
   - [ ] 可視化預覽（在圖片上繪製範例圓圈）
6. [ ] 建立模板資料結構類別
   - [ ] TemplateBuilder class
   - [ ] 資料驗證
7. [ ] 基礎UI佈局和樣式

**Deliverables**:
- `template-builder.html` - 模板建立器獨立頁面（或整合進index.html的tab）
- `assets/js/template-builder.js` - 模板建立器主邏輯
- `assets/js/coordinate-picker.js` - 座標拾取功能
- `assets/css/template-builder.css` - 樣式

---

### Stage 5: 🆕 模板建立工具 - 欄位區塊（Template Builder - Part 2）

**Goal**: 實現fieldBlocks新增/移除功能

**Success Criteria**:
- [ ] 可新增各種類型的欄位區塊
- [ ] 支援所有fieldType（MCQ4/5, INT, CUSTOM）
- [ ] 支援fieldLabels範圍語法（q1..10）
- [ ] 可設定各種參數（origin, direction, gaps）
- [ ] 可移除已新增的欄位區塊
- [ ] 即時在圖片上預覽bubble位置

**Tasks**:
1. [ ] 建立欄位區塊新增UI
   - [ ] 區塊名稱輸入
   - [ ] 起始座標輸入（可使用已選座標）
   - [ ] fieldType下拉選單
   - [ ] fieldLabels輸入（支援範圍語法）
   - [ ] 方向選擇（horizontal/vertical）
   - [ ] 間距設定（bubblesGap, labelsGap）
2. [ ] 實現fieldLabels解析器
   - [ ] 解析單一標籤（q1）
   - [ ] 解析範圍（q1..10）
   - [ ] 解析逗號分隔列表
3. [ ] 實現bubble位置計算
   - [ ] 根據origin和gaps計算所有bubble座標
   - [ ] 考慮direction（水平/垂直佈局）
4. [ ] 實現即時預覽
   - [ ] 在參考圖上繪製所有bubble圓圈
   - [ ] 顏色標記不同區塊
   - [ ] 顯示題號/選項標籤
5. [ ] 建立欄位區塊列表顯示
   - [ ] 顯示所有已新增的區塊
   - [ ] 每個區塊的詳細資訊
6. [ ] 實現區塊移除功能
   - [ ] 選擇區塊
   - [ ] 移除按鈕
   - [ ] 更新預覽
7. [ ] 資料驗證
   - [ ] 檢查區塊重疊
   - [ ] 檢查座標超出範圍

**Deliverables**:
- 更新 `assets/js/template-builder.js` - 欄位區塊邏輯
- `assets/js/field-labels-parser.js` - 標籤解析器
- `assets/js/bubble-position-calculator.js` - bubble座標計算
- `assets/js/template-visualizer.js` - 模板視覺化

---

### Stage 6: 🆕 模板建立工具 - 進階功能（Template Builder - Part 3）

**Goal**: 完成customLabels、preProcessors和匯出功能

**Success Criteria**:
- [ ] 可新增/移除自訂標籤
- [ ] 可新增/移除前處理器
- [ ] 可匯出完整的template.json
- [ ] 模板視覺化完整且準確

**Tasks**:
1. [ ] 實現自訂標籤功能
   - [ ] 新增customLabel UI
   - [ ] customLabel資料結構
   - [ ] 顯示已新增的customLabels
   - [ ] 移除功能
2. [ ] 實現前處理器功能
   - [ ] preprocessor類型選擇（CropPage等）
   - [ ] options設定（JSON格式）
   - [ ] preprocessors列表顯示
   - [ ] 移除功能
3. [ ] 完善模板視覺化
   - [ ] 顯示所有fieldBlocks
   - [ ] 顯示customLabels關聯
   - [ ] 圖例說明
   - [ ] 縮放/平移功能
4. [ ] 實現template.json匯出
   - [ ] 組裝完整的JSON結構
   - [ ] 資料驗證
   - [ ] 生成downloadable檔案
   - [ ] 檔案命名
5. [ ] 範例模板載入
   - [ ] 預設範例模板
   - [ ] 載入已有template.json
   - [ ] 解析並填入UI
6. [ ] 完整測試
   - [ ] 建立各種類型模板測試
   - [ ] 匯出/載入循環測試

**Deliverables**:
- 更新 `assets/js/template-builder.js` - 完整功能
- `assets/js/template-exporter.js` - template匯出邏輯
- `assets/js/template-importer.js` - template載入解析
- `templates/examples/` - 範例模板集合

---

### Stage 7: 🆕 空白答案卡產生器（Sheet Generator）

**Goal**: 實現單張空白答案卡自動產生功能

**Success Criteria**:
- [ ] 可設定題目數量、類型、欄數
- [ ] 可選擇是否包含QR Code
- [ ] 可自訂3行標題文字
- [ ] 可選擇是否包含對齊標記
- [ ] 自動產生空白答案卡PNG圖檔
- [ ] 同時產生對應的template.json
- [ ] 可下載圖檔和模板

**Tasks**:
1. [ ] 建立答案卡產生器UI
   - [ ] 題目設定區塊（數量、類型、欄數）
   - [ ] QR Code設定
   - [ ] 自訂文字輸入（3行）
   - [ ] 對齊標記選項
   - [ ] 進階設定（頁面尺寸、圓圈大小）
   - [ ] 產生按鈕
2. [ ] 實現Canvas繪製邏輯
   - [ ] 頁面背景繪製
   - [ ] 對齊標記繪製（四角黑色方塊）
   - [ ] 標題文字繪製
   - [ ] 題號繪製
   - [ ] 選項標籤繪製（A/B/C/D或0-9）
   - [ ] bubble圓圈繪製
3. [ ] 實現QR Code生成
   - [ ] 整合QR Code library（qrcode.js）
   - [ ] QR Code內容編碼
   - [ ] QR Code位置計算
   - [ ] QR Code繪製到Canvas
4. [ ] 實現答案卡佈局計算
   - [ ] 根據題目數量和欄數計算佈局
   - [ ] 自動調整間距
   - [ ] 邊界計算
5. [ ] 自動產生template.json
   - [ ] 根據佈局計算fieldBlocks
   - [ ] 產生正確的座標
   - [ ] 包含所有必要欄位
6. [ ] 實現下載功能
   - [ ] Canvas轉PNG
   - [ ] template.json下載
   - [ ] 檔案命名（含時間戳）
7. [ ] 預覽功能
   - [ ] 即時預覽答案卡
   - [ ] 縮放查看細節

**Deliverables**:
- `sheet-generator.html` - 答案卡產生器頁面
- `assets/js/sheet-generator.js` - 主邏輯
- `assets/js/qrcode-handler.js` - QR Code處理
- `assets/js/canvas-drawer.js` - Canvas繪製工具
- `assets/lib/qrcode.min.js` - QR Code函式庫

---

### Stage 8: 🆕 批次答案卡產生器（Batch Generator）

**Goal**: 從學生名單批次產生專屬答案卡

**Success Criteria**:
- [ ] 可上傳Excel/CSV學生名單
- [ ] 可指定ID欄位和資料欄位
- [ ] 為每位學生產生專屬答案卡（含QR Code）
- [ ] QR Code編碼學生ID
- [ ] 可印上學生個人資料
- [ ] 打包所有圖檔和模板為ZIP下載

**Tasks**:
1. [ ] 整合Excel/CSV解析器
   - [ ] 使用SheetJS (xlsx.js)
   - [ ] 解析Excel (.xlsx, .xls)
   - [ ] 解析CSV
   - [ ] 資料表格顯示預覽
2. [ ] 建立批次產生UI
   - [ ] 檔案上傳
   - [ ] 欄位對應設定
   - [ ] 答案卡設定（複用Generator設定）
   - [ ] 資料預覽表格
   - [ ] 產生按鈕
3. [ ] 實現學生資料處理
   - [ ] 解析ID欄位
   - [ ] 解析資料欄位
   - [ ] 驗證資料完整性
4. [ ] 實現批次繪製
   - [ ] 遍歷每位學生
   - [ ] 生成個人化QR Code（學生ID）
   - [ ] 印上學生資料（姓名、班級等）
   - [ ] 批次進度顯示
5. [ ] 實現ZIP打包
   - [ ] 使用JSZip函式庫
   - [ ] 打包所有答案卡圖檔
   - [ ] 打包template.json
   - [ ] 加入README說明檔
6. [ ] 批次下載功能
   - [ ] 生成ZIP檔案
   - [ ] 自動下載
   - [ ] 檔案命名（含日期）
7. [ ] 進度和錯誤處理
   - [ ] 批次進度條
   - [ ] 各個學生處理狀態
   - [ ] 錯誤記錄和處理

**Deliverables**:
- `batch-generator.html` - 批次產生器頁面
- `assets/js/batch-generator.js` - 主邏輯
- `assets/js/excel-parser.js` - Excel/CSV解析
- `assets/js/zip-packager.js` - ZIP打包
- `assets/lib/xlsx.min.js` - SheetJS函式庫
- `assets/lib/jszip.min.js` - JSZip函式庫

---

### Stage 9: 🔧 整合、測試與優化

**Goal**: 整合所有功能、全面測試、效能優化、準備部署

**Success Criteria**:
- [ ] 所有功能整合到統一介面
- [ ] 功能間資料互通（如：Generator產生的template可用於Processing）
- [ ] 完整的使用者指南
- [ ] 範例檔案齊全
- [ ] 效能優化完成
- [ ] 成功部署到GitHub Pages

**Tasks**:
1. [ ] 統一UI/UX整合
   - [ ] 建立Tab導航系統
   - [ ] 統一設計語言
   - [ ] 響應式設計完善
2. [ ] 功能互通實現
   - [ ] Template Builder → Processing (使用建立的模板)
   - [ ] Generator → Processing (使用產生的模板)
   - [ ] Batch Generator → Processing (批次辨識)
   - [ ] 模板庫共享（存在IndexedDB）
3. [ ] 完整使用者指南
   - [ ] 各功能詳細說明
   - [ ] 圖文教學
   - [ ] 常見問題FAQ
   - [ ] 影片教學（可選）
4. [ ] 範例檔案準備
   - [ ] 範例template.json (多種類型)
   - [ ] 範例config.json
   - [ ] 範例evaluation.json
   - [ ] 範例答案卡圖檔
   - [ ] 範例學生名單Excel/CSV
5. [ ] 效能優化
   - [ ] Canvas繪製優化
   - [ ] 批次處理優化（分批、暫停）
   - [ ] 記憶體管理優化
   - [ ] IndexedDB查詢優化
6. [ ] 全面測試
   - [ ] 功能測試（每個feature）
   - [ ] 整合測試（功能間互動）
   - [ ] 效能測試（大檔案、批次處理）
   - [ ] 跨瀏覽器測試
   - [ ] 行動裝置測試
7. [ ] 部署準備
   - [ ] 最終版本README
   - [ ] GitHub Pages設定
   - [ ] 部署測試
   - [ ] 線上版本驗證

**Deliverables**:
- 完整的`index.html` - 統一入口
- `docs/USER_GUIDE.md` - 完整使用者指南
- `docs/FEATURES.md` - 功能特色說明
- `samples/` - 完整範例檔案集
- 部署到GitHub Pages的線上版本

---

## 📊 功能對照表

| 功能分類 | Gradio版本功能 | Web版本現狀 | 優先級 |
|---------|--------------|-----------|--------|
| **辨識功能** | | | |
| 單張影像處理 | ✅ | ✅ | - |
| 批次影像處理 | ✅ | ❌ | P0 |
| template.json | ✅ | ✅ | - |
| config.json | ✅ | ❌ | P1 |
| evaluation.json | ✅ | ❌ | P1 |
| 自訂marker | ✅ | ❌ | P2 |
| 圖片Gallery | ✅ | ❌ | P1 |
| 詳細記錄 | ✅ | ❌ | P1 |
| **模板建立** | | | |
| 參考圖檔上傳 | ✅ | ❌ | P0 |
| 點擊取座標 | ✅ | ❌ | P0 |
| 尺寸設定 | ✅ | ❌ | P0 |
| 欄位區塊編輯 | ✅ | ❌ | P0 |
| 自訂標籤 | ✅ | ❌ | P1 |
| 前處理器 | ✅ | ❌ | P2 |
| 模板視覺化 | ✅ | ❌ | P0 |
| 模板匯出 | ✅ | ❌ | P0 |
| **答案卡產生** | | | |
| 空白卡產生 | ✅ | ❌ | P0 |
| QR Code | ✅ | ❌ | P1 |
| 自訂文字 | ✅ | ❌ | P1 |
| 對齊標記 | ✅ | ❌ | P1 |
| **批次產生** | | | |
| Excel/CSV解析 | ✅ | ❌ | P0 |
| 個人化答案卡 | ✅ | ❌ | P0 |
| 學生資料印製 | ✅ | ❌ | P1 |
| ZIP打包下載 | ✅ | ❌ | P0 |

---

## 🗓️ 實施時程估計

| Stage | 主要內容 | 預估工時 | 優先級 |
|-------|---------|---------|--------|
| Stage 1-2 | 基礎建設（已完成） | - | ✅ |
| Stage 3 | 完善辨識功能 | 12小時 | P0 |
| Stage 4 | 模板建立器-基礎 | 16小時 | P0 |
| Stage 5 | 模板建立器-欄位 | 20小時 | P0 |
| Stage 6 | 模板建立器-進階 | 12小時 | P1 |
| Stage 7 | 空白卡產生器 | 16小時 | P0 |
| Stage 8 | 批次產生器 | 20小時 | P0 |
| Stage 9 | 整合測試部署 | 16小時 | P0 |

**總計**: 約 112 小時（14個工作天）

---

## 🔧 技術依賴（新增）

### 必要函式庫
- **OpenCV.js**: v4.9.0+ ✅ 已有
- **QRCode.js**: QR Code生成 (qrcode.js)
- **SheetJS**: Excel/CSV解析 (xlsx.js)
- **JSZip**: ZIP檔案打包 (jszip.js)

### 選用函式庫
- **Fabric.js**: Canvas互動編輯（模板建立器可視化）
- **Papa Parse**: CSV解析（替代方案）
- **FileSaver.js**: 檔案下載增強

---

## ✅ 完成標準

專案視為完成當：

1. [ ] **功能完整性**: 所有4個Tab（Processing, Template Builder, Generator, Batch）功能完整實現
2. [ ] **功能對等性**: 100%複製Gradio版本所有核心功能
3. [ ] **測試通過**: 所有功能測試用例通過
4. [ ] **文件完整**: 完整的使用者指南和範例
5. [ ] **效能達標**:
   - 單張影像處理 < 3秒
   - 批次處理10張 < 30秒
   - 產生10張答案卡 < 10秒
6. [ ] **部署成功**: 成功部署到GitHub Pages並可公開訪問
7. [ ] **跨平台**: 在主流瀏覽器（Chrome, Firefox, Safari, Edge）和行動裝置正常運作

---

## 📝 備註

### 與原計劃的主要差異

1. **功能範圍擴大**: 從單純的「影像辨識」擴展到完整的「OMR系統」
2. **新增3個主要模組**: Template Builder, Sheet Generator, Batch Generator
3. **Stage數量增加**: 從8個Stage增加到9個Stage
4. **工時增加**: 從40小時增加到112小時

### 優先級說明

- **P0 (最高)**: 核心功能，必須實現
- **P1 (高)**: 重要功能，強烈建議實現
- **P2 (中)**: 增強功能，可後續優化

### 實施策略

建議分階段實施：
1. **第一階段**: 完成Stage 3-5（完善辨識+模板建立器基礎和欄位編輯）
2. **第二階段**: 完成Stage 7-8（答案卡產生器+批次產生器）
3. **第三階段**: 完成Stage 6+9（模板建立器進階+整合測試）

---

**建立日期**: 2025-10-05
**版本**: 2.0 - 完整功能版本
**負責人**: PM (Claude)
