# OMRChecker Serverless Web - 技術文件

## 專案概述

本專案旨在將 OMRChecker 完全網頁化，使用 **OpenCV.js** 進行 OMR（光學標記識別）處理，所有運算都在瀏覽器端執行，**不需要任何後端伺服器**。

### 核心特性

✅ **100% 靜態網頁** - 可直接開啟 HTML 或放在 GitHub Pages
✅ **無伺服器依賴** - 所有處理都在瀏覽器端完成
✅ **離線可用** - 下載後可完全離線使用
✅ **跨平台** - 任何支援現代瀏覽器的裝置都可運行
✅ **隱私保護** - 影像資料不會上傳到任何伺服器

---

## 技術架構

### 1. 技術棧選擇

| 技術 | 用途 | 理由 |
|------|------|------|
| **Vanilla JavaScript** | 核心邏輯 | 無需編譯，純靜態部署 |
| **OpenCV.js (WASM)** | 影像處理 | 高效能的瀏覽器端 CV 庫 |
| **IndexedDB** | 資料儲存 | 瀏覽器本地資料庫，支援大容量 |
| **Web Workers** | 並行處理 | 避免阻塞 UI 線程 |
| **HTML5 Canvas** | 影像渲染 | 原生影像顯示和處理 |

### 2. 專案結構

```
serverless_web/
├── index.html                 # 主頁面
├── assets/
│   ├── css/
│   │   └── style.css         # 樣式表
│   ├── js/
│   │   ├── app.js            # 主應用程式
│   │   ├── opencv-loader.js  # OpenCV.js 載入器
│   │   ├── image-processor.js # 影像處理模組
│   │   ├── storage.js        # IndexedDB 封裝
│   │   └── export.js         # 結果匯出（CSV/JSON）
│   └── lib/
│       └── opencv.js         # OpenCV.js 庫（約 8MB）
├── workers/
│   └── image-worker.js       # Web Worker 處理腳本
├── templates/
│   └── default-template.json # 預設 OMR 模板
└── README.md
```

---

## OpenCV.js 核心技術

### 1. 載入與初始化

**方法一：從 CDN 載入（需網路）**

```html
<!DOCTYPE html>
<html>
<head>
    <title>OMR Checker</title>
</head>
<body>
    <div id="status">正在載入 OpenCV.js...</div>

    <script>
    var Module = {
        onRuntimeInitialized() {
            document.getElementById('status').textContent = 'OpenCV.js 已就緒';
            console.log('OpenCV 版本:', cv.getBuildInformation());
        }
    };
    </script>

    <!-- CDN 載入 -->
    <script async src="https://docs.opencv.org/4.x/opencv.js"></script>
</body>
</html>
```

**方法二：本地載入（完全離線）**

```html
<!-- 將 opencv.js 下載到本地 assets/lib/ -->
<script async src="./assets/lib/opencv.js"></script>
```

### 2. 影像處理核心流程

#### 步驟 1: 影像上傳與讀取

```javascript
// assets/js/image-processor.js

class ImageProcessor {
    constructor() {
        this.currentImage = null;
    }

    // 從檔案讀取影像
    loadImageFromFile(file) {
        return new Promise((resolve, reject) => {
            // 驗證檔案
            if (!this.validateFile(file)) {
                reject(new Error('不支援的檔案格式'));
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    this.currentImage = img;
                    resolve(img);
                };
                img.onerror = reject;
                img.src = e.target.result;
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    // 檔案驗證
    validateFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!validTypes.includes(file.type)) return false;
        if (file.size > maxSize) return false;

        return true;
    }

    // 從 Image 物件創建 cv.Mat
    imageToMat(imgElement) {
        return cv.imread(imgElement);
    }
}
```

#### 步驟 2: 影像預處理

```javascript
// 灰階轉換 + 降噪 + 二值化
function preprocessImage(src) {
    const gray = new cv.Mat();
    const blurred = new cv.Mat();
    const binary = new cv.Mat();

    try {
        // 1. 轉灰階
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);

        // 2. 高斯模糊降噪
        const ksize = new cv.Size(5, 5);
        cv.GaussianBlur(gray, blurred, ksize, 0);

        // 3. 自適應二值化（處理光照不均）
        cv.adaptiveThreshold(
            blurred,
            binary,
            255,
            cv.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv.THRESH_BINARY,
            11,
            2
        );

        return binary; // 呼叫者負責釋放

    } finally {
        gray.delete();
        blurred.delete();
    }
}
```

#### 步驟 3: 輪廓檢測 - 找答案卡邊界

```javascript
function findAnswerSheetContour(binary) {
    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    let result = null;

    try {
        // 尋找輪廓
        cv.findContours(
            binary,
            contours,
            hierarchy,
            cv.RETR_EXTERNAL,
            cv.CHAIN_APPROX_SIMPLE
        );

        // 找最大的四邊形輪廓
        let maxArea = 0;

        for (let i = 0; i < contours.size(); i++) {
            const contour = contours.get(i);
            const area = cv.contourArea(contour);

            // 計算多邊形近似
            const peri = cv.arcLength(contour, true);
            const approx = new cv.Mat();
            cv.approxPolyDP(contour, approx, 0.02 * peri, true);

            // 檢查是否為四邊形且面積最大
            if (approx.rows === 4 && area > maxArea) {
                maxArea = area;
                if (result) result.delete();
                result = approx;
            } else {
                approx.delete();
            }
        }

        return result; // 返回四個角點

    } finally {
        contours.delete();
        hierarchy.delete();
    }
}
```

#### 步驟 4: 透視變換 - 校正傾斜

```javascript
function correctPerspective(src, corners) {
    const dst = new cv.Mat();

    try {
        // 提取四個角點座標
        const points = [];
        for (let i = 0; i < 4; i++) {
            points.push({
                x: corners.data32F[i * 2],
                y: corners.data32F[i * 2 + 1]
            });
        }

        // 排序角點（左上、右上、右下、左下）
        const sorted = sortCorners(points);

        // 計算目標尺寸（保持寬高比）
        const width = Math.max(
            distance(sorted[0], sorted[1]),
            distance(sorted[2], sorted[3])
        );
        const height = Math.max(
            distance(sorted[0], sorted[3]),
            distance(sorted[1], sorted[2])
        );

        // 定義來源和目標點
        const srcPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
            sorted[0].x, sorted[0].y,
            sorted[1].x, sorted[1].y,
            sorted[2].x, sorted[2].y,
            sorted[3].x, sorted[3].y
        ]);

        const dstPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
            0, 0,
            width, 0,
            width, height,
            0, height
        ]);

        // 計算並應用透視變換
        const M = cv.getPerspectiveTransform(srcPoints, dstPoints);
        cv.warpPerspective(
            src,
            dst,
            M,
            new cv.Size(width, height),
            cv.INTER_LINEAR,
            cv.BORDER_CONSTANT,
            new cv.Scalar()
        );

        // 清理
        srcPoints.delete();
        dstPoints.delete();
        M.delete();

        return dst;

    } catch (e) {
        dst.delete();
        throw e;
    }
}

// 輔助函數：排序角點
function sortCorners(points) {
    // 按 y 座標排序
    points.sort((a, b) => a.y - b.y);

    // 上方兩點按 x 排序
    const top = points.slice(0, 2).sort((a, b) => a.x - b.x);
    // 下方兩點按 x 排序
    const bottom = points.slice(2, 4).sort((a, b) => a.x - b.x);

    return [
        top[0],    // 左上
        top[1],    // 右上
        bottom[1], // 右下
        bottom[0]  // 左下
    ];
}

// 輔助函數：計算兩點距離
function distance(p1, p2) {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy);
}
```

#### 步驟 5: 標記檢測

```javascript
function detectAnswerMarks(binary, template) {
    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    const marks = [];

    try {
        cv.findContours(
            binary,
            contours,
            hierarchy,
            cv.RETR_LIST,
            cv.CHAIN_APPROX_SIMPLE
        );

        for (let i = 0; i < contours.size(); i++) {
            const contour = contours.get(i);
            const area = cv.contourArea(contour);

            // 根據模板過濾標記大小
            if (area > template.minArea && area < template.maxArea) {
                const rect = cv.boundingRect(contour);
                const aspectRatio = rect.width / rect.height;

                // 接近正方形或圓形
                if (aspectRatio > 0.8 && aspectRatio < 1.2) {
                    // 計算填充率（判斷是否已標記）
                    const fillRatio = area / (rect.width * rect.height);

                    marks.push({
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        area: area,
                        filled: fillRatio > template.fillThreshold
                    });
                }
            }
        }

        return marks;

    } finally {
        contours.delete();
        hierarchy.delete();
    }
}
```

---

## Web Workers 並行處理

### 主線程代碼

```javascript
// assets/js/app.js

class OMRApp {
    constructor() {
        this.worker = null;
        this.initWorker();
    }

    initWorker() {
        this.worker = new Worker('./workers/image-worker.js');

        this.worker.onmessage = (e) => {
            const { type, data, error } = e.data;

            switch (type) {
                case 'ready':
                    console.log('Worker 已就緒');
                    this.onWorkerReady();
                    break;

                case 'progress':
                    this.updateProgress(data.percent, data.message);
                    break;

                case 'result':
                    this.displayResult(data);
                    break;

                case 'error':
                    this.handleError(error);
                    break;
            }
        };

        this.worker.onerror = (error) => {
            console.error('Worker 錯誤:', error);
        };
    }

    async processImage(file) {
        // 讀取檔案
        const arrayBuffer = await file.arrayBuffer();

        // 發送到 Worker 處理
        this.worker.postMessage({
            type: 'process',
            imageData: arrayBuffer,
            template: this.currentTemplate
        }, [arrayBuffer]); // 轉移所有權，提升效能
    }

    updateProgress(percent, message) {
        document.getElementById('progress').value = percent;
        document.getElementById('status').textContent = message;
    }

    displayResult(result) {
        console.log('處理結果:', result);
        // 顯示結果邏輯...
    }
}
```

### Worker 腳本

```javascript
// workers/image-worker.js

importScripts('../assets/lib/opencv.js');

let opencvReady = false;

// OpenCV.js 載入完成
self.Module = {
    onRuntimeInitialized() {
        opencvReady = true;
        self.postMessage({ type: 'ready' });
    }
};

// 接收主線程訊息
self.onmessage = async function(e) {
    const { type, imageData, template } = e.data;

    if (!opencvReady && type !== 'init') {
        self.postMessage({
            type: 'error',
            error: 'OpenCV 尚未載入完成'
        });
        return;
    }

    if (type === 'process') {
        processOMRSheet(imageData, template);
    }
};

function processOMRSheet(arrayBuffer, template) {
    try {
        // 進度報告
        reportProgress(10, '載入影像...');

        // 從 ArrayBuffer 創建影像
        const img = createImageFromBuffer(arrayBuffer);
        const src = cv.imread(img);

        reportProgress(20, '預處理影像...');
        const binary = preprocessImage(src);

        reportProgress(40, '偵測答案卡邊界...');
        const corners = findAnswerSheetContour(binary);

        if (!corners) {
            throw new Error('無法偵測到答案卡邊界');
        }

        reportProgress(60, '校正透視...');
        const corrected = correctPerspective(src, corners);

        reportProgress(80, '識別答案標記...');
        const marks = detectAnswerMarks(corrected, template);

        reportProgress(90, '解析結果...');
        const result = parseAnswers(marks, template);

        reportProgress(100, '完成！');

        // 回傳結果
        self.postMessage({
            type: 'result',
            data: result
        });

        // 清理記憶體
        src.delete();
        binary.delete();
        corners.delete();
        corrected.delete();

    } catch (error) {
        self.postMessage({
            type: 'error',
            error: error.message
        });
    }
}

function reportProgress(percent, message) {
    self.postMessage({
        type: 'progress',
        data: { percent, message }
    });
}

function createImageFromBuffer(buffer) {
    const blob = new Blob([buffer], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.src = url;
    return img;
}

// ... 其他處理函數（preprocessImage, findAnswerSheetContour 等）
```

---

## IndexedDB 資料儲存

```javascript
// assets/js/storage.js

class OMRStorage {
    constructor() {
        this.dbName = 'OMRCheckerDB';
        this.version = 1;
        this.db = null;
    }

    // 初始化資料庫
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // 創建 results 表
                if (!db.objectStoreNames.contains('results')) {
                    const store = db.createObjectStore('results', {
                        keyPath: 'id',
                        autoIncrement: true
                    });

                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('filename', 'filename', { unique: false });
                }

                // 創建 templates 表
                if (!db.objectStoreNames.contains('templates')) {
                    const store = db.createObjectStore('templates', {
                        keyPath: 'name'
                    });
                }
            };
        });
    }

    // 儲存處理結果
    async saveResult(data) {
        const transaction = this.db.transaction(['results'], 'readwrite');
        const store = transaction.objectStore('results');

        const record = {
            timestamp: Date.now(),
            filename: data.filename,
            imageBlob: data.imageBlob, // 直接儲存 Blob
            result: data.result,
            metadata: data.metadata
        };

        return new Promise((resolve, reject) => {
            const request = store.add(record);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // 讀取所有結果
    async getAllResults() {
        const transaction = this.db.transaction(['results'], 'readonly');
        const store = transaction.objectStore('results');

        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // 刪除結果
    async deleteResult(id) {
        const transaction = this.db.transaction(['results'], 'readwrite');
        const store = transaction.objectStore('results');

        return new Promise((resolve, reject) => {
            const request = store.delete(id);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    // 儲存模板
    async saveTemplate(template) {
        const transaction = this.db.transaction(['templates'], 'readwrite');
        const store = transaction.objectStore('templates');

        return new Promise((resolve, reject) => {
            const request = store.put(template);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    // 讀取模板
    async getTemplate(name) {
        const transaction = this.db.transaction(['templates'], 'readonly');
        const store = transaction.objectStore('templates');

        return new Promise((resolve, reject) => {
            const request = store.get(name);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
}
```

---

## 結果匯出功能

```javascript
// assets/js/export.js

class ResultExporter {
    // 匯出為 CSV
    exportToCSV(results) {
        const headers = ['編號', '檔案名稱', '時間', '答案'];
        const rows = results.map((r, i) => [
            i + 1,
            r.filename,
            new Date(r.timestamp).toLocaleString(),
            r.result.answers.join(',')
        ]);

        const csv = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');

        this.downloadFile(csv, 'omr-results.csv', 'text/csv');
    }

    // 匯出為 JSON
    exportToJSON(results) {
        const json = JSON.stringify(results, null, 2);
        this.downloadFile(json, 'omr-results.json', 'application/json');
    }

    // 匯出為 Excel (使用 SheetJS - 需引入 xlsx.js)
    exportToExcel(results) {
        const ws = XLSX.utils.json_to_sheet(
            results.map((r, i) => ({
                '編號': i + 1,
                '檔案名稱': r.filename,
                '時間': new Date(r.timestamp).toLocaleString(),
                '答案': r.result.answers.join(','),
                '分數': r.result.score
            }))
        );

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Results');
        XLSX.writeFile(wb, 'omr-results.xlsx');
    }

    // 下載檔案
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();

        URL.revokeObjectURL(url);
    }
}
```

---

## 完整 HTML 範例

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OMR Checker - 線上答案卡辨識</title>
    <link rel="stylesheet" href="./assets/css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>📝 OMR Checker</h1>
            <p>完全在瀏覽器端運行的答案卡辨識系統</p>
        </header>

        <main>
            <!-- 狀態指示器 -->
            <div id="opencv-status" class="status">
                <span id="status-text">正在載入 OpenCV.js...</span>
            </div>

            <!-- 檔案上傳區 -->
            <div id="upload-zone" class="upload-zone" style="display:none">
                <div class="drop-area">
                    <input type="file" id="file-input" accept="image/*" multiple>
                    <label for="file-input">
                        <svg><!-- 上傳圖示 --></svg>
                        <p>拖放圖片到此處或點擊上傳</p>
                    </label>
                </div>
            </div>

            <!-- 處理進度 -->
            <div id="progress-container" style="display:none">
                <progress id="progress" value="0" max="100"></progress>
                <p id="progress-text">處理中...</p>
            </div>

            <!-- 結果顯示 -->
            <div id="results-container" style="display:none">
                <h2>辨識結果</h2>
                <div id="results"></div>

                <div class="actions">
                    <button id="export-csv">匯出 CSV</button>
                    <button id="export-json">匯出 JSON</button>
                    <button id="clear-all">清除全部</button>
                </div>
            </div>

            <!-- 預覽畫布 -->
            <div id="canvas-container">
                <canvas id="canvas-output"></canvas>
            </div>
        </main>
    </div>

    <!-- 載入腳本 -->
    <script>
        var Module = {
            onRuntimeInitialized() {
                document.getElementById('status-text').textContent = 'OpenCV.js 已就緒';
                document.getElementById('upload-zone').style.display = 'block';
            }
        };
    </script>
    <script async src="./assets/lib/opencv.js"></script>
    <script src="./assets/js/storage.js"></script>
    <script src="./assets/js/export.js"></script>
    <script src="./assets/js/image-processor.js"></script>
    <script src="./assets/js/app.js"></script>
</body>
</html>
```

---

## 部署方案 - 純靜態網站

### 選項 1: GitHub Pages（推薦）

**完全免費、無需伺服器、支援自訂域名**

```bash
# 1. 建立 GitHub 倉庫
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的帳號/omr-checker.git
git push -u origin main

# 2. 啟用 GitHub Pages
# 到 Settings > Pages > Source > 選擇 main branch

# 3. 訪問網站
# https://你的帳號.github.io/omr-checker/
```

### 選項 2: 本地開啟

**下載後直接雙擊 index.html 即可使用**

```bash
# 確保所有資源路徑是相對路徑
# 瀏覽器會顯示警告，但仍可正常運行
```

### 選項 3: 簡易 HTTP 伺服器（開發用）

```bash
# Python 3
python3 -m http.server 8000

# Node.js
npx serve

# 訪問 http://localhost:8000
```

---

## 效能優化建議

### 1. OpenCV.js 載入優化

```javascript
// 使用 CDN 快取
<script async src="https://cdn.jsdelivr.net/npm/@techstark/opencv-js@4.9.0-release.0/opencv.js"></script>

// 或本地壓縮版本
<script async src="./assets/lib/opencv.min.js"></script>
```

### 2. 影像尺寸優化

```javascript
function resizeImageIfNeeded(img, maxDimension = 1920) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    let { width, height } = img;

    if (width > maxDimension || height > maxDimension) {
        const scale = maxDimension / Math.max(width, height);
        width *= scale;
        height *= scale;
    }

    canvas.width = width;
    canvas.height = height;
    ctx.drawImage(img, 0, 0, width, height);

    return canvas;
}
```

### 3. 記憶體管理

```javascript
// 使用 try-finally 確保記憶體釋放
function processImage(src) {
    const gray = new cv.Mat();
    const binary = new cv.Mat();

    try {
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
        cv.threshold(gray, binary, 127, 255, cv.THRESH_BINARY);
        return binary.clone(); // 返回副本
    } finally {
        // 確保釋放
        gray.delete();
        binary.delete();
    }
}
```

---

## 瀏覽器兼容性

| 瀏覽器 | 最低版本 | 支援狀況 |
|--------|---------|---------|
| Chrome | 67+ | ✅ 完全支援 |
| Firefox | 79+ | ✅ 完全支援 |
| Safari | 14+ | ✅ 完全支援 |
| Edge | 79+ | ✅ 完全支援 |
| IE | - | ❌ 不支援 |

**必要功能檢測:**
- WebAssembly
- Web Workers
- IndexedDB
- Canvas API

```javascript
// 功能檢測
function checkBrowserSupport() {
    const required = {
        wasm: typeof WebAssembly !== 'undefined',
        workers: typeof Worker !== 'undefined',
        indexedDB: 'indexedDB' in window,
        canvas: !!document.createElement('canvas').getContext
    };

    const unsupported = Object.entries(required)
        .filter(([, supported]) => !supported)
        .map(([feature]) => feature);

    if (unsupported.length > 0) {
        alert(`您的瀏覽器不支援: ${unsupported.join(', ')}`);
        return false;
    }

    return true;
}
```

---

## 模板配置格式

```json
{
  "name": "標準答案卡",
  "version": "1.0",
  "dimensions": {
    "width": 600,
    "height": 800
  },
  "questions": 50,
  "optionsPerQuestion": 4,
  "markDetection": {
    "minArea": 100,
    "maxArea": 1000,
    "fillThreshold": 0.6
  },
  "layout": {
    "startX": 50,
    "startY": 100,
    "columnSpacing": 30,
    "rowSpacing": 20
  },
  "answerKey": ["A", "B", "C", "D", "A", "..."]
}
```

---

## 安全性注意事項

### 1. 檔案驗證

```javascript
function validateUploadedFile(file) {
    // 檢查 Magic Number（檔案簽名）
    const reader = new FileReader();

    return new Promise((resolve, reject) => {
        reader.onload = (e) => {
            const arr = new Uint8Array(e.target.result).subarray(0, 4);
            const header = Array.from(arr)
                .map(b => b.toString(16).padStart(2, '0'))
                .join('');

            // JPEG: ffd8ff, PNG: 89504e47
            if (header.startsWith('ffd8ff') || header.startsWith('89504e47')) {
                resolve(true);
            } else {
                reject(new Error('檔案格式不符'));
            }
        };

        reader.readAsArrayBuffer(file.slice(0, 4));
    });
}
```

### 2. 資料隱私

✅ **優勢：**
- 所有資料留在本機瀏覽器
- 不會上傳任何影像到伺服器
- IndexedDB 資料只儲存在使用者裝置

⚠️ **注意：**
- 清除瀏覽器資料會刪除所有結果
- 建議定期匯出備份

---

## 常見問題 FAQ

### Q1: 為什麼首次載入很慢？
A: OpenCV.js 約 8MB，首次載入需要時間。載入後會被瀏覽器快取。

### Q2: 可以離線使用嗎？
A: 可以！將整個資料夾下載後即可離線使用。

### Q3: 處理速度如何？
A: 取決於裝置效能，一般電腦約 1-3 秒/張。

### Q4: 支援批次處理嗎？
A: 支援，可同時選擇多個檔案上傳。

### Q5: 資料會不會外洩？
A: 不會，所有處理都在本機瀏覽器完成，不會傳送任何資料到伺服器。

---

## 參考資源

1. **OpenCV.js 官方文件**: https://docs.opencv.org/4.x/d5/d10/tutorial_js_root.html
2. **MDN Web Workers**: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API
3. **MDN IndexedDB**: https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API
4. **GitHub Pages 部署**: https://pages.github.com/

---

## 授權

本專案基於 OMRChecker 開源專案，採用 MIT License。
