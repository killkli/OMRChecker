# 字體檔案 / Font Files

## 中文字體支援 / Chinese Font Support

本專案需要繁體中文字體來正確顯示 OMR 答案卡上的中文文字。

### 安裝字體 / Font Installation

#### 選項 1：使用專案內建字體（推薦）

將 TW-Kai.ttf（台灣標楷體）放入此目錄：

```bash
# 從系統字體複製（macOS）
cp ~/Library/Fonts/edukai-4.0.ttf fonts/TW-Kai.ttf

# 或從系統字體複製（Linux）
cp /usr/share/fonts/truetype/tw-kai/edukai-4.0.ttf fonts/TW-Kai.ttf
```

#### 選項 2：下載開源字體

如果系統沒有標楷體，可以下載開源的思源宋體或文泉驛正黑：

**思源宋體（Noto Serif CJK TC）:**
```bash
cd fonts
wget https://github.com/googlefonts/noto-cjk/raw/main/Serif/OTF/TraditionalChinese/NotoSerifCJKtc-Regular.otf -O TW-Kai.ttf
```

**文泉驛正黑（WenQuanYi Zen Hei）:**
```bash
cd fonts
wget https://github.com/anthonyfok/fonts-wqy-zenhei/raw/master/wqy-zenhei.ttc -O TW-Kai.ttf
```

#### 選項 3：使用系統字體（自動 fallback）

如果 `fonts/TW-Kai.ttf` 不存在，系統會自動嘗試使用以下字體：

**macOS:**
- `/Users/[username]/Library/Fonts/edukai-4.0.ttf` (標楷體)
- `/System/Library/Fonts/Supplemental/Songti.ttc` (宋體)
- `/System/Library/Fonts/STHeiti Medium.ttc` (黑體)

**Linux:**
- `/usr/share/fonts/truetype/tw-kai/edukai-4.0.ttf`
- `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`
- `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`

**Windows:**
- `C:\Windows\Fonts\kaiu.ttf` (標楷體)
- `C:\Windows\Fonts\mingliu.ttc` (細明體)
- `C:\Windows\Fonts\msjh.ttc` (微軟正黑體)

### 字體檔案資訊

- **檔案名稱**: TW-Kai.ttf
- **建議字體**: 台灣標楷體 (edukai-4.0)
- **檔案大小**: 約 15 MB
- **授權**: 開放原始碼（視字體而定）

### 注意事項

1. 字體檔案因為體積較大（15MB），不包含在 Git 儲存庫中
2. 請在部署時確保已安裝字體檔案
3. 如果沒有中文字體，系統會使用預設字體（可能無法正確顯示中文）

### 測試字體

測試字體是否正確載入：

```bash
# 執行 Gradio 介面並查看 log
cd frontend
python app.py

# 查看 log 中是否顯示 "Using font: ..."
```

### 字體授權

- **edukai (標楷體)**: Arphic Public License
- **Noto Sans CJK**: SIL Open Font License 1.1
- **WenQuanYi Zen Hei**: GPL v2 with font embedding exception

請確保使用的字體符合您的使用情境授權要求。
