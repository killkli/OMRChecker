# 學生資料批次產生指南

## 功能說明

批次產生 OMR 答案卡時，除了 QR Code ID 外，還可以在每張答案卡上印上個別學生的資料（如姓名、班級等）。

## Excel/CSV 檔案格式

### 範例格式

```csv
student_id,name,class,section
S001,Alice Wang,Grade 10,A
S002,Bob Chen,Grade 10,A
S003,Carol Li,Grade 10,B
S004,David Zhang,Grade 10,B
S005,Emma Liu,Grade 10,C
```

### 欄位說明

- **第一欄（或指定的 ID 欄）**：學生 ID，會被編碼到 QR Code 中
- **其他欄位**：學生資料，會印在答案卡上

## Gradio 界面使用方式

### 1. 上傳檔案
在 "📦 Batch Generate Sheets" 標籤中上傳 Excel 或 CSV 檔案

### 2. 設定欄位

#### ID Column Name (ID 欄位名稱)
- 輸入包含學生 ID 的欄位名稱
- 例如：`student_id`
- 留空則使用第一欄

#### Student Data Columns (學生資料欄位)
- 輸入要印在答案卡上的欄位名稱（逗號分隔）
- 例如：`name,class,section`
- 留空則使用所有欄位（除了 ID）

### 3. 自訂標題（可選）
- **Header Text Line 1**：共用標題（粗體、大字）
  - 例如：`期末考試 - 數學科`
- **Header Text Line 2**：共用副標題
  - 例如：`考試時間：90 分鐘`
- **Header Text Line 3**：其他資訊
  - 例如：`日期：_____ 分數：_____`

### 4. 配置答案卡參數
- 題目數量、題型、欄位數等

### 5. 產生批次
- 點擊 "🚀 Generate Batch Sheets"
- 下載 ZIP 檔案

## 輸出結果

### 每張答案卡包含：

1. **共用標題**（如果有設定）
   ```
   期末考試 - 數學科
   考試時間：90 分鐘
   日期：_____ 分數：_____
   ```

2. **個別學生資料**（從 Excel 讀取）
   ```
   name: Alice Wang
   class: Grade 10
   section: A
   ```

3. **題目區塊**
   - 根據設定的題數和題型產生

4. **QR Code**（右下角）
   - 內容：學生 ID（如 `S001`）

### ZIP 檔案結構

```
generated_sheets.zip
├── sheets/
│   ├── S001.png
│   ├── S002.png
│   ├── S003.png
│   └── ...
└── templates/
    ├── S001_template.json
    ├── S002_template.json
    ├── S003_template.json
    └── ...
```

## 使用範例

### 範例 1：基本使用（所有欄位）

**Excel 內容：**
```
student_id,name,class
S001,Alice,10A
S002,Bob,10B
```

**設定：**
- ID Column Name: `student_id`
- Student Data Columns: 留空（使用所有欄位）

**結果：每張答案卡會顯示**
```
name: Alice
class: 10A
[QR Code: S001]
```

### 範例 2：選擇特定欄位

**Excel 內容：**
```
student_id,name,class,phone,email
S001,Alice,10A,1234567,alice@example.com
```

**設定：**
- ID Column Name: `student_id`
- Student Data Columns: `name,class`（只印姓名和班級）

**結果：每張答案卡會顯示**
```
name: Alice
class: 10A
[QR Code: S001]
```

### 範例 3：含共用標題

**設定：**
- Header Text Line 1: `期末考試 - 數學科`
- Header Text Line 2: `班級：_____ 座號：_____`
- Student Data Columns: `name`

**結果：每張答案卡會顯示**
```
        期末考試 - 數學科
      班級：_____ 座號：_____

name: Alice Wang

[題目區塊]

            [QR Code: S001]
```

## 注意事項

1. **Excel 欄位名稱**：確保欄位名稱與設定中輸入的一致（區分大小寫）
2. **空值處理**：如果某個學生的資料欄位為空，該欄位不會顯示在答案卡上
3. **中文支援**：支援中文欄位名稱和內容
4. **文字位置**：
   - 共用標題：置中顯示於頂部
   - 學生資料：靠左顯示於標題下方
   - QR Code：右下角
5. **文字大小**：
   - 標題第一行：大字、粗體
   - 標題其他行：中字、正常
   - 學生資料：小字、正常

## 疑難排解

### 問題：找不到欄位
**錯誤訊息**：`Column 'xxx' not found`

**解決方法**：
- 檢查 Excel 檔案中的欄位名稱拼寫
- 確認欄位名稱沒有多餘的空格
- 使用 Excel 查看實際的欄位名稱

### 問題：學生資料沒有顯示
**可能原因**：
- Student Data Columns 欄位留空，但 ID Column Name 也留空
- 欄位名稱拼寫錯誤

**解決方法**：
- 明確指定 Student Data Columns
- 檢查欄位名稱

### 問題：文字重疊
**解決方法**：
- 減少學生資料欄位數量
- 調整 Page Height 增加空間
- 減少共用標題行數

## 進階技巧

### 技巧 1：製作班級座位表
在 Excel 中加入座號欄位：
```
student_id,name,seat_no
S001,Alice,1
S002,Bob,2
```

### 技巧 2：多語言支援
可以使用任何 UTF-8 支援的語言：
```
student_id,姓名,班級
S001,王小明,十年級 A 班
S002,李小華,十年級 B 班
```

### 技巧 3：條件式欄位
在 Excel 中使用公式產生欄位：
```
=IF(gender="M", "Male", "Female")
```
然後匯出為 CSV 使用
