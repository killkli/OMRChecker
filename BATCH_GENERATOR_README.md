# Batch OMR Sheet Generator

批次產生帶有 QR Code 的 OMR 答案卡，可從 Excel 或 CSV 檔案讀取學生 ID 列表。

## 功能特點

- 從 Excel (.xlsx, .xls) 或 CSV 檔案讀取 ID 列表
- 為每個 ID 自動產生獨立的 OMR 答案卡
- 每張答案卡包含該 ID 的 QR Code
- 自動產生對應的 template JSON 檔案
- 支援自訂題目數量、題型、版面配置等

## 安裝依賴

```bash
pip install pandas openpyxl qrcode[pil]
```

## 使用方法

### 基本用法

```bash
python batch_generate_sheets.py student_ids.csv -o output_folder
```

### 完整範例

```bash
python batch_generate_sheets.py student_ids.xlsx \
  -o generated_sheets \
  -q 20 \
  -t QTYPE_MCQ4 \
  --columns 4 \
  --page-width 2100 \
  --page-height 2970
```

## 參數說明

### 必要參數

- `excel_file`: Excel 或 CSV 檔案路徑，包含學生 ID 列表

### 選用參數

**輸出設定:**
- `-o, --output-dir`: 輸出目錄 (預設: `generated_sheets`)

**Excel 讀取設定:**
- `-c, --column`: 包含 ID 的欄位名稱 (預設: 第一欄)
- `-s, --sheet`: Excel 工作表名稱或索引 (預設: 0，第一個工作表)

**答案卡設定:**
- `-q, --questions`: 題目數量 (預設: 20)
- `-t, --type`: 題型 (預設: QTYPE_MCQ4)
  - `QTYPE_MCQ4`: 4 選項選擇題
  - `QTYPE_MCQ5`: 5 選項選擇題
  - `QTYPE_INT`: 數字填空題
- `--columns`: 版面欄位數 (預設: 4)
- `--no-markers`: 停用對齊標記
- `--page-width`: 頁面寬度 (像素，預設: 2100)
- `--page-height`: 頁面高度 (像素，預設: 2970)
- `--bubble-size`: 圓圈大小 (像素，預設: 40)

## Excel/CSV 檔案格式

### CSV 範例 (student_ids.csv)

```csv
student_id
S001
S002
S003
S004
S005
```

### Excel 範例

| student_id | name | class |
|------------|------|-------|
| S001       | Alice| 10A   |
| S002       | Bob  | 10A   |
| S003       | Carol| 10B   |

使用特定欄位：
```bash
python batch_generate_sheets.py students.xlsx -c student_id
```

## 輸出結構

```
generated_sheets/
├── sheets/              # 產生的答案卡圖片
│   ├── S001.png
│   ├── S002.png
│   └── S003.png
└── templates/           # 對應的 template JSON 檔案
    ├── S001_template.json
    ├── S002_template.json
    └── S003_template.json
```

## 使用範例

### 範例 1: 產生 10 題、2 欄的簡單答案卡

```bash
python batch_generate_sheets.py student_ids.csv \
  -o test_output \
  -q 10 \
  --columns 2
```

### 範例 2: 產生 30 題、5 選項的答案卡

```bash
python batch_generate_sheets.py student_ids.xlsx \
  -q 30 \
  -t QTYPE_MCQ5 \
  --columns 5
```

### 範例 3: 從特定欄位讀取 ID

```bash
python batch_generate_sheets.py students.xlsx \
  -c "學號" \
  -s "109學年" \
  -o output_109
```

### 範例 4: 不使用對齊標記

```bash
python batch_generate_sheets.py student_ids.csv \
  --no-markers \
  -o output_no_markers
```

## 處理生成的答案卡

生成答案卡後，可以使用 OMRChecker 處理掃描的答案卡：

```bash
# 將掃描的答案卡放入 inputs/ 目錄
# 將對應的 template JSON 放入 inputs/template.json

python main.py -i inputs/ --outputDir outputs/
```

## 常見問題

**Q: 如何修改 QR Code 的大小？**

A: QR Code 大小會根據 `--bubble-size` 自動調整（約為 bubble_size * 5），建議使用預設值。

**Q: 支援哪些 Excel 格式？**

A: 支援 .xlsx, .xls (需要 openpyxl), 和 .csv 格式。

**Q: 如何確認 QR Code 內容正確？**

A: 使用手機 QR Code 掃描器，或查看對應的 template JSON 檔案中的 `bubbleValues` 欄位。

**Q: 可以批次產生不同題數的答案卡嗎？**

A: 目前一次批次只能產生相同格式的答案卡。如需不同格式，請分別執行多次。

## 效能建議

- 產生 100 張答案卡約需 1-2 分鐘
- 建議一次產生不超過 500 張
- 大量產生時可考慮分批處理

## 技術細節

- 使用 `frontend.app.OMRSheetGenerator` 產生答案卡
- QR Code 使用 `qrcode` 函式庫產生
- 支援 marker-based 和 non-marker 兩種模式
- 自動計算版面配置和座標系統
