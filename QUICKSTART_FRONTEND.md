# 🚀 Gradio Frontend Quick Start

## 啟動前端介面

### 方法 1: 使用啟動腳本（推薦）

```bash
python run_frontend.py
```

### 方法 2: 直接運行應用

```bash
python frontend/app.py
```

介面會自動在瀏覽器中打開，地址為：`http://localhost:7860`

---

## 使用步驟

### 1. 上傳 OMR 圖片
點擊「**OMR Images**」區域，選擇一張或多張 PNG/JPG 格式的 OMR 答題卡圖片。

### 2. 上傳模板文件（必需）
點擊「**Template File (template.json)**」，上傳你的模板配置文件。

### 3. 上傳可選配置文件
展開「**Optional Configuration Files**」，可以上傳：
- **config.json**: 自定義圖像處理參數
- **evaluation.json**: 答案鑰匙和評分規則

### 4. 設置處理選項
展開「**Processing Options**」，可以啟用：
- **Enable Auto-Alignment**: 自動對齊（實驗性功能）
- **Set Layout Mode**: 顯示模板佈局而不是處理

### 5. 開始處理
點擊「**🚀 Process OMR Sheets**」按鈕。

### 6. 查看結果
處理完成後，右側會顯示：
- **Status**: 處理狀態和摘要
- **Results CSV**: 可下載的結果文件
- **Marked OMR Images**: 標記後的圖片預覽
- **Processing Log**: 詳細處理日誌（可展開查看）

---

## 功能特色

✅ **批量處理** - 一次上傳多張圖片同時處理
✅ **視覺化結果** - 直接在網頁上查看標記後的圖片
✅ **CSV 下載** - 輕鬆下載處理結果
✅ **純 Python** - 不需要 JavaScript，使用 Gradio 框架
✅ **自動清理** - 臨時文件自動刪除，不佔用空間

---

## 示例數據測試

項目提供了多個示例數據集，您可以用來測試前端：

```bash
# 示例數據位於 samples 目錄
samples/
├── sample2/
├── sample3/
├── sample4/
└── sample5/
```

每個示例目錄都包含：
- OMR 圖片
- template.json
- 可能還有 config.json 和 evaluation.json

**建議**: 先用 `samples/sample2/` 測試前端功能。

---

## 文件說明

### 必需文件

1. **OMR 圖片** (PNG/JPG)
   - 掃描或拍攝的答題卡
   - 需要與模板佈局匹配

2. **template.json**
   - 定義答題卡的氣泡佈局
   - 必須是有效的 JSON 格式

### 可選文件

1. **config.json**
   - 自定義調整參數
   - 圖像處理設置

2. **evaluation.json**
   - 答案定義
   - 評分規則

---

## 疑難排解

### 介面無法啟動
```bash
# 確保安裝所有依賴
pip install -r requirements.txt
```

### 處理錯誤
- 檢查 template.json 是否為有效的 JSON
- 確保圖片與模板佈局匹配
- 查看「Processing Log」中的錯誤訊息

### 無結果顯示
- 確認處理成功完成
- 檢查模板是否與圖片匹配
- 先用範例數據測試

---

## 技術細節

- **框架**: Gradio 5.0+
- **後端**: 複用現有 OMRChecker 處理管道
- **端口**: 7860 (可在代碼中修改)
- **臨時文件**: 自動創建和清理

---

## 更多資訊

- 詳細文檔: `frontend/README.md`
- 實施計劃: `IMPLEMENTATION_PLAN.md`
- 主項目: [OMRChecker GitHub](https://github.com/Udayraj123/OMRChecker)

---

**祝使用愉快！** 🎉
