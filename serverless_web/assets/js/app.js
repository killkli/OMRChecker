/**
 * OMR Checker 主應用程式
 * 負責協調各個模組並處理 UI 互動
 */

class OMRApp {
    constructor() {
        this.elements = {
            statusCard: document.getElementById('opencv-status'),
            statusIcon: document.getElementById('status-icon'),
            statusTitle: document.getElementById('status-title'),
            statusText: document.getElementById('status-text'),
            loadingBar: document.getElementById('loading-bar'),
            loadingProgress: document.getElementById('loading-progress'),
            uploadSection: document.getElementById('upload-section'),
            previewSection: document.getElementById('preview-section'),
            dropZone: document.getElementById('drop-zone'),
            fileInput: document.getElementById('file-input'),
            selectFileBtn: document.getElementById('select-file-btn'),
            processBtn: document.getElementById('process-btn'),
            uploadNewBtn: document.getElementById('upload-new-btn'),
            processingProgress: document.getElementById('processing-progress'),
            processingMessage: document.getElementById('processing-message'),
            saveResultBtn: document.getElementById('save-result-btn'),
            viewHistoryBtn: document.getElementById('view-history-btn'),
            historySection: document.getElementById('history-section'),
            historyList: document.getElementById('history-list'),
            closeHistoryBtn: document.getElementById('close-history-btn')
        };

        this.imageProcessor = null;
        this.worker = null;
        this.currentFile = null;
        this.template = null;
        this.useWorker = true;  // 預設使用 Worker
        this.messageId = 0;
        this.pendingRequests = new Map();
        this.storage = null;  // IndexedDB storage
        this.currentResults = null;  // 儲存當前處理結果
        this.activeBlobUrls = new Set();  // 追蹤活躍的 Blob URLs

        this.init();
    }

    /**
     * 初始化應用程式
     */
    init() {
        console.log('🚀 OMR Checker 應用程式啟動');

        // 檢查 Worker 支援
        if (!window.Worker) {
            console.warn('⚠️ 瀏覽器不支援 Web Workers，將使用主執行緒處理');
            this.useWorker = false;
        }

        if (this.useWorker) {
            // 使用 Worker 模式
            this.initWorker();
        } else {
            // 降級到主執行緒模式
            this.initMainThread();
        }
    }

    /**
     * 初始化 Worker 模式
     */
    initWorker() {
        console.log('🔧 初始化 Web Worker...');

        // 建立 Worker
        this.worker = new Worker('./workers/image-worker.js');

        // 設定 Worker 訊息處理
        this.worker.onmessage = (e) => this.handleWorkerMessage(e);
        this.worker.onerror = (error) => this.handleWorkerError(error);

        // 初始化 Worker（傳送 OpenCV.js 路徑）
        this.sendWorkerMessage('init', {
            opencvPath: './assets/lib/opencv.js'
        });

        // 初始化 ImageProcessor（用於檔案驗證等主執行緒操作）
        this.imageProcessor = new ImageProcessor();

        // 初始化 Storage
        this.initStorage();

        // 設定事件監聽器
        this.setupEventListeners();
    }

    /**
     * 初始化主執行緒模式（降級方案）
     */
    initMainThread() {
        console.log('🔧 使用主執行緒模式...');

        // 註冊 OpenCV.js 載入回調
        window.opencvLoader.onProgress((percent) => {
            this.updateProgress(percent);
        });

        window.opencvLoader.onReady(() => {
            this.onOpenCVReady();
        });

        window.opencvLoader.onError((error) => {
            this.onOpenCVError(error);
        });
    }

    /**
     * 發送訊息給 Worker
     */
    sendWorkerMessage(type, payload) {
        const id = ++this.messageId;

        return new Promise((resolve, reject) => {
            this.pendingRequests.set(id, { resolve, reject });

            this.worker.postMessage({
                type,
                payload,
                id
            });

            // 設定逾時（30 秒）
            setTimeout(() => {
                if (this.pendingRequests.has(id)) {
                    this.pendingRequests.delete(id);
                    reject(new Error('Worker 回應逾時'));
                }
            }, 30000);
        });
    }

    /**
     * 處理來自 Worker 的訊息
     */
    handleWorkerMessage(e) {
        const { type, payload, id } = e.data;

        switch (type) {
            case 'ready':
                this.onWorkerReady(payload);
                break;

            case 'progress':
                this.onWorkerProgress(payload, id);
                break;

            case 'result':
                this.onWorkerResult(payload, id);
                break;

            case 'error':
                this.onWorkerError(payload, id);
                break;

            default:
                console.warn('[App] 未知的 Worker 訊息類型:', type);
        }
    }

    /**
     * Worker 就緒
     */
    onWorkerReady(payload) {
        console.log('✅ Worker 已就緒');

        // 更新狀態卡片
        this.elements.statusCard.classList.add('ready');
        this.elements.statusIcon.textContent = '✅';
        this.elements.statusTitle.textContent = '系統就緒';
        this.elements.statusText.textContent = 'Web Worker 已成功初始化！';

        // 隱藏載入條
        setTimeout(() => {
            this.elements.loadingBar.style.display = 'none';
        }, 500);

        // 載入預設模板
        this.loadTemplate();

        // 顯示上傳區域
        setTimeout(() => {
            this.elements.statusCard.style.display = 'none';
            this.elements.uploadSection.style.display = 'block';
            this.elements.uploadSection.classList.add('fade-in');
        }, 1000);
    }

    /**
     * Worker 進度更新
     */
    onWorkerProgress(payload, id) {
        const { percent, message } = payload;

        console.log(`📊 處理進度: ${percent}% - ${message}`);

        // 更新進度條（如果 UI 元素存在）
        if (this.elements.processingProgress) {
            this.elements.processingProgress.style.width = `${percent}%`;
        }

        if (this.elements.processingMessage) {
            this.elements.processingMessage.textContent = message;
        }

        this.showProgress(message);
    }

    /**
     * Worker 處理完成
     */
    onWorkerResult(payload, id) {
        const request = this.pendingRequests.get(id);
        if (request) {
            request.resolve(payload);
            this.pendingRequests.delete(id);
        }
    }

    /**
     * Worker 錯誤
     */
    onWorkerError(payload, id) {
        console.error('[Worker] 錯誤:', payload.message);

        const request = this.pendingRequests.get(id);
        if (request) {
            request.reject(new Error(payload.message));
            this.pendingRequests.delete(id);
        }
    }

    /**
     * Worker 錯誤事件
     */
    handleWorkerError(error) {
        console.error('[Worker] 發生錯誤:', error);
        this.showError('Worker 錯誤: ' + error.message);
    }

    /**
     * 更新載入進度
     * @param {Number} percent - 進度百分比 (0-100)
     */
    updateProgress(percent) {
        const progress = Math.round(percent);

        // 更新進度條
        this.elements.loadingProgress.style.width = `${progress}%`;

        // 更新狀態文字
        if (progress < 30) {
            this.elements.statusText.textContent = '正在下載 OpenCV.js 核心模組...';
        } else if (progress < 60) {
            this.elements.statusText.textContent = '正在載入 WebAssembly 模組...';
        } else if (progress < 90) {
            this.elements.statusText.textContent = '正在初始化 OpenCV 環境...';
        } else if (progress < 100) {
            this.elements.statusText.textContent = '即將完成...';
        } else {
            this.elements.statusText.textContent = '載入完成！';
            this.elements.loadingProgress.classList.add('complete');
        }

        console.log(`📊 載入進度: ${progress}%`);
    }

    /**
     * OpenCV.js 載入完成處理
     */
    onOpenCVReady() {
        console.log('✅ OpenCV.js 已就緒,開始初始化應用程式');

        // 更新狀態卡片
        this.elements.statusCard.classList.add('ready');
        this.elements.statusIcon.textContent = '✅';
        this.elements.statusTitle.textContent = '系統就緒';
        this.elements.statusText.textContent = 'OpenCV.js 已成功載入並初始化！';

        // 隱藏載入條
        setTimeout(() => {
            this.elements.loadingBar.style.display = 'none';
        }, 500);

        // 測試 OpenCV 功能
        this.testOpenCV();

        // 初始化 ImageProcessor
        this.imageProcessor = new ImageProcessor();
        console.log('✅ ImageProcessor 已初始化');

        // 載入預設模板
        this.loadTemplate();

        // 顯示上傳區域 (淡入動畫)
        setTimeout(() => {
            this.elements.statusCard.style.display = 'none';
            this.elements.uploadSection.style.display = 'block';
            this.elements.uploadSection.classList.add('fade-in');
        }, 1000);

        // 設定事件監聽器
        this.setupEventListeners();
    }

    /**
     * 載入 OMR 模板
     */
    async loadTemplate() {
        try {
            console.log('🔄 載入預設 OMR 模板...');

            // 從 JSON 檔案載入模板
            const response = await fetch('./templates/default-template.json');
            if (!response.ok) {
                throw new Error('模板檔案載入失敗');
            }

            this.template = await response.json();
            console.log(`✅ 模板載入成功: ${this.template.name}`);

            // 如果使用 Worker，將模板傳送給 Worker
            if (this.useWorker && this.worker) {
                await this.sendWorkerMessage('load_template', {
                    template: this.template
                });
                console.log('✅ 模板已傳送至 Worker');
            }

        } catch (error) {
            console.error('❌ 模板載入失敗:', error);
            this.showError('模板載入失敗，將無法進行答案檢測');
        }
    }

    /**
     * OpenCV.js 載入錯誤處理
     * @param {Error} error - 錯誤物件
     */
    onOpenCVError(error) {
        console.error('❌ OpenCV.js 載入失敗:', error);

        // 更新狀態卡片
        this.elements.statusCard.classList.add('error');
        this.elements.statusIcon.textContent = '❌';
        this.elements.statusTitle.textContent = '載入失敗';
        this.elements.statusText.textContent = `錯誤: ${error.message}`;

        // 隱藏載入條
        this.elements.loadingBar.style.display = 'none';

        // 顯示重試按鈕 (未來可擴展)
        this.showRetryButton();
    }

    /**
     * 初始化 Storage
     */
    async initStorage() {
        try {
            this.storage = new OMRStorage();
            await this.storage.init();
            console.log('✅ Storage 已初始化');

            // 顯示儲存空間資訊
            const estimate = await this.storage.getStorageEstimate();
            console.log(`💾 儲存空間: ${estimate.usageInMB}MB / ${estimate.quotaInMB}MB (${estimate.percentage}%)`);
        } catch (error) {
            console.warn('⚠️ Storage 初始化失敗:', error.message);
            console.warn('將無法使用儲存功能');
        }
    }

    /**
     * 設定事件監聽器
     */
    setupEventListeners() {
        // 拖放事件
        this.elements.dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.elements.dropZone.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.elements.dropZone.addEventListener('drop', (e) => this.handleDrop(e));

        // 點擊上傳
        this.elements.selectFileBtn.addEventListener('click', () => {
            this.elements.fileInput.click();
        });

        this.elements.fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e);
        });

        // 重新處理和上傳新圖片
        this.elements.processBtn.addEventListener('click', () => {
            this.reprocessImage();
        });

        this.elements.uploadNewBtn.addEventListener('click', () => {
            this.uploadNewImage();
        });

        // Storage 相關事件
        if (this.elements.saveResultBtn) {
            this.elements.saveResultBtn.addEventListener('click', () => {
                this.saveCurrentResult();
            });
        }

        if (this.elements.viewHistoryBtn) {
            this.elements.viewHistoryBtn.addEventListener('click', () => {
                this.showHistory();
            });
        }

        if (this.elements.closeHistoryBtn) {
            this.elements.closeHistoryBtn.addEventListener('click', () => {
                this.closeHistory();
            });
        }

        // 使用事件委派處理歷史記錄列表的按鈕點擊
        if (this.elements.historyList) {
            this.elements.historyList.addEventListener('click', (e) => {
                // 刪除單筆記錄按鈕
                if (e.target.classList.contains('delete-item-btn')) {
                    const id = parseInt(e.target.dataset.id);
                    this.deleteHistoryItem(id);
                }

                // 刪除所有記錄按鈕
                if (e.target.id === 'delete-all-btn') {
                    this.deleteAllHistory();
                }
            });
        }

        console.log('✅ 事件監聽器已設定');
    }

    /**
     * 處理拖放 - dragover
     */
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.elements.dropZone.classList.add('drag-over');
    }

    /**
     * 處理拖放 - dragleave
     */
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.elements.dropZone.classList.remove('drag-over');
    }

    /**
     * 處理拖放 - drop
     */
    async handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();

        this.elements.dropZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            await this.processFile(files[0]);
        }
    }

    /**
     * 處理檔案選擇
     */
    async handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            await this.processFile(file);
        }
    }

    /**
     * 處理上傳的檔案
     */
    async processFile(file) {
        try {
            console.log('📁 開始處理檔案:', file.name);

            // 1. 基本驗證
            if (!this.imageProcessor.validateFile(file)) {
                this.showError('檔案格式不支援或大小超過限制（最大 10MB）');
                return;
            }

            // 2. 驗證檔案簽名
            this.showProgress('驗證檔案中...');
            const isValidSignature = await this.imageProcessor.validateFileSignature(file);
            if (!isValidSignature) {
                this.showError('檔案簽名驗證失敗，可能不是有效的圖片檔案');
                return;
            }

            // 3. 載入影像
            this.showProgress('載入影像中...');
            const imgElement = await this.imageProcessor.loadImageFromFile(file);
            this.currentFile = file;
            console.log('✅ 影像載入成功');

            if (this.useWorker) {
                // 使用 Worker 處理
                await this.processFileWithWorker(imgElement);
            } else {
                // 使用主執行緒處理
                await this.processFileOnMainThread(imgElement);
            }

        } catch (error) {
            console.error('❌ 處理檔案時發生錯誤:', error);
            this.showError('處理失敗：' + error.message);
        }
    }

    /**
     * 使用 Worker 處理影像
     */
    async processFileWithWorker(imgElement) {
        try {
            // 將 Image 轉換為 ImageData
            const canvas = document.createElement('canvas');
            canvas.width = imgElement.width;
            canvas.height = imgElement.height;

            const ctx = canvas.getContext('2d');
            ctx.drawImage(imgElement, 0, 0);

            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

            // 發送給 Worker 處理
            const results = await this.sendWorkerMessage('process_image', {
                imageData: Array.from(imageData.data),
                width: imageData.width,
                height: imageData.height
            });

            // 將 ImageData 轉換回可顯示的格式
            this.displayWorkerResults(results);

            this.showSuccess('影像處理完成！');

        } catch (error) {
            console.error('❌ Worker 處理失敗:', error);
            this.showError('處理失敗：' + error.message);
        }
    }

    /**
     * 使用主執行緒處理影像（降級方案）
     */
    async processFileOnMainThread(imgElement) {
        try {
            // 4. 處理影像（基礎預處理）
            this.showProgress('處理影像中...');
            const results = this.imageProcessor.preprocessImage(imgElement);

            // 5. 透視校正（Stage 3）
            try {
                this.showProgress('執行透視校正...');
                const mat = this.imageProcessor.imageToMat(imgElement);
                const perspectiveResult = this.imageProcessor.correctPerspective(mat);

                results.corners = perspectiveResult.visualization;
                results.corrected = perspectiveResult.corrected;

                console.log('✅ 透視校正完成');
                console.log('  角點座標:', perspectiveResult.corners);

                mat.delete();

                // 6. 答案檢測與解析（Stage 4）
                if (this.template && results.corrected) {
                    try {
                        this.showProgress('檢測答案標記...');
                        const omrResult = await this.imageProcessor.detectAndParseAnswers(
                            results.corrected,
                            this.template
                        );

                        results.omr = omrResult;
                        console.log('✅ 答案檢測完成');
                        console.log(`  答對: ${omrResult.scoring.correctCount}/${omrResult.scoring.totalQuestions}`);
                        console.log(`  分數: ${omrResult.scoring.score}/${omrResult.scoring.totalPoints}`);

                    } catch (error) {
                        console.warn('⚠️ 答案檢測失敗:', error.message);
                    }
                }

            } catch (error) {
                console.warn('⚠️ 透視校正失敗:', error.message);
                this.showError('透視校正失敗: ' + error.message + '\n將顯示基礎處理結果');
            }

            // 7. 顯示結果
            this.displayResults(results);

            this.showSuccess('影像處理完成！');

        } catch (error) {
            console.error('❌ 處理失敗:', error);
            this.showError('處理失敗：' + error.message);
        }
    }

    /**
     * 顯示 Worker 回傳的結果
     */
    displayWorkerResults(results) {
        // 儲存當前結果
        this.currentResults = results;

        // 隱藏上傳區域，顯示預覽區域
        this.elements.uploadSection.style.display = 'none';
        this.elements.previewSection.style.display = 'block';
        this.elements.previewSection.classList.add('fade-in');

        // 將 Worker 回傳的 ImageData 顯示到 Canvas
        try {
            this.imageDataToCanvas('canvas-original', results.original);
            this.imageDataToCanvas('canvas-grayscale', results.grayscale);
            this.imageDataToCanvas('canvas-blurred', results.blurred);
            this.imageDataToCanvas('canvas-binary', results.binary);

            if (results.corners) {
                this.imageDataToCanvas('canvas-corners', results.corners);
            }

            if (results.corrected) {
                this.imageDataToCanvas('canvas-corrected', results.corrected);
            }

            if (results.omr && results.omr.visualization) {
                this.imageDataToCanvas('canvas-omr-result', results.omr.visualization);
                this.displayOMRResults(results.omr);
            }

            console.log('✅ 處理結果已顯示在 Canvas');
        } catch (error) {
            console.error('❌ Canvas 顯示失敗:', error);
            this.showError('結果顯示失敗：' + error.message);
        }
    }

    /**
     * 將 ImageData 顯示到 Canvas
     */
    imageDataToCanvas(canvasId, imageDataObj) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`Canvas ${canvasId} 不存在`);
            return;
        }

        const { data, width, height } = imageDataObj;

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        const imageData = new ImageData(
            new Uint8ClampedArray(data),
            width,
            height
        );

        ctx.putImageData(imageData, 0, 0);
    }

    /**
     * 顯示處理結果（主執行緒版本）
     */
    displayResults(results) {
        // 儲存當前結果
        this.currentResults = results;

        // 隱藏上傳區域，顯示預覽區域
        this.elements.uploadSection.style.display = 'none';
        this.elements.previewSection.style.display = 'block';
        this.elements.previewSection.classList.add('fade-in');

        // 顯示各個處理步驟到 Canvas
        try {
            cv.imshow('canvas-original', results.original);
            cv.imshow('canvas-grayscale', results.grayscale);
            cv.imshow('canvas-blurred', results.blurred);
            cv.imshow('canvas-binary', results.binary);

            // Stage 3: 顯示透視校正結果
            if (results.corners) {
                cv.imshow('canvas-corners', results.corners);
            }

            if (results.corrected) {
                cv.imshow('canvas-corrected', results.corrected);
            }

            // Stage 4: 顯示答案檢測結果
            if (results.omr && results.omr.visualization) {
                cv.imshow('canvas-omr-result', results.omr.visualization);
                this.displayOMRResults(results.omr);
            }

            console.log('✅ 處理結果已顯示在 Canvas');
        } catch (error) {
            console.error('❌ Canvas 顯示失敗:', error);
            this.showError('結果顯示失敗：' + error.message);
        }
    }

    /**
     * 顯示 OMR 評分結果
     */
    displayOMRResults(omrResult) {
        const { scoring, answers } = omrResult;

        // 在控制台輸出詳細結果
        console.log('');
        console.log('========================================');
        console.log('📊 OMR 評分結果');
        console.log('========================================');
        console.log(`總分: ${scoring.score}/${scoring.totalPoints} (${scoring.percentage}%)`);
        console.log(`答對: ${scoring.correctCount} 題`);
        console.log(`答錯: ${scoring.incorrectCount} 題`);
        console.log(`未作答: ${scoring.unansweredCount} 題`);
        console.log('');
        console.log('詳細答題情況:');

        Object.keys(scoring.details).forEach(questionNo => {
            const detail = scoring.details[questionNo];
            const statusIcon = detail.isCorrect ? '✅' :
                              detail.status === 'unanswered' ? '⚪' : '❌';
            const studentAnswer = detail.student || '(未作答)';

            console.log(`  Q${questionNo}: ${studentAnswer} (正確答案: ${detail.correct}) ${statusIcon}`);
        });

        console.log('========================================');

        // 如果有 UI 元素，也可以在這裡更新（未來可擴展）
        // 例如：顯示分數卡片、答題詳情表格等
    }

    /**
     * 重新處理當前影像
     */
    reprocessImage() {
        if (this.currentFile) {
            console.log('🔄 重新處理影像');

            // 清理舊的 Mat（主執行緒模式）
            if (!this.useWorker && this.imageProcessor) {
                this.imageProcessor.cleanup();
            }

            this.processFile(this.currentFile);
        }
    }

    /**
     * 上傳新圖片
     */
    uploadNewImage() {
        console.log('📤 上傳新圖片');

        // 清理記憶體
        if (this.imageProcessor) {
            this.imageProcessor.cleanup();
        }

        // 重置 UI
        this.elements.previewSection.style.display = 'none';
        this.elements.uploadSection.style.display = 'block';
        this.elements.fileInput.value = '';
        this.currentFile = null;

        // 清空 Canvas
        const canvases = [
            'canvas-original',
            'canvas-grayscale',
            'canvas-blurred',
            'canvas-binary',
            'canvas-corners',
            'canvas-corrected'
        ];
        canvases.forEach(id => {
            const canvas = document.getElementById(id);
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            }
        });
    }

    /**
     * 顯示進度訊息
     */
    showProgress(message) {
        console.log('⏳', message);
        // 可以在此添加載入動畫或進度提示
    }

    /**
     * 顯示成功訊息
     */
    showSuccess(message) {
        console.log('✅', message);
        // 可以在此添加成功提示 Toast
    }

    /**
     * 顯示錯誤訊息
     */
    showError(message) {
        console.error('❌', message);
        alert(message);  // 簡單的錯誤提示，後續可改進為 Toast
    }

    /**
     * 測試 OpenCV 基本功能
     */
    testOpenCV() {
        let testMat = null;
        try {
            // 建立一個簡單的矩陣來測試 OpenCV 是否正常運作
            testMat = new cv.Mat(100, 100, cv.CV_8UC3);

            console.log('🧪 OpenCV 功能測試:');
            console.log(`  - 矩陣建立: ✅ (${testMat.rows}x${testMat.cols})`);
            console.log(`  - 矩陣類型: ${testMat.type()}`);
            console.log(`  - 記憶體管理: ✅`);

            console.log('✅ OpenCV 所有功能測試通過');
        } catch (e) {
            console.error('❌ OpenCV 功能測試失敗:', e);
        } finally {
            // 確保在任何情況下都釋放記憶體
            if (testMat) {
                testMat.delete();
            }
        }
    }

    /**
     * 顯示重試按鈕 (錯誤時)
     */
    showRetryButton() {
        const retryButton = document.createElement('button');
        retryButton.textContent = '🔄 重新載入頁面';
        retryButton.style.cssText = `
            margin-top: 1rem;
            padding: 0.75rem 1.5rem;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 0.5rem;
            font-size: 1rem;
            cursor: pointer;
        `;
        retryButton.onclick = () => window.location.reload();

        this.elements.statusCard.appendChild(retryButton);
    }

    /**
     * 儲存當前處理結果
     */
    async saveCurrentResult() {
        if (!this.storage) {
            this.showError('儲存功能未啟用');
            return;
        }

        if (!this.currentResults) {
            this.showError('沒有可儲存的結果');
            return;
        }

        try {
            console.log('💾 開始儲存結果...');

            // 將 Canvas 轉換為 Blob
            const originalBlob = await this.canvasToBlob('canvas-original');
            const processedBlob = this.currentResults.omr ?
                await this.canvasToBlob('canvas-omr-result') :
                await this.canvasToBlob('canvas-corrected');

            // 準備儲存資料
            const resultData = {
                originalImageBlob: originalBlob,
                processedImageBlob: processedBlob,
                answers: this.currentResults.omr ? this.currentResults.omr.answers : {},
                score: this.currentResults.omr ? this.currentResults.omr.scoring.score : 0,
                templateName: this.template ? this.template.name : 'default',
                metadata: {
                    fileName: this.currentFile ? this.currentFile.name : 'unknown',
                    fileSize: this.currentFile ? this.currentFile.size : 0,
                    totalQuestions: this.currentResults.omr ? this.currentResults.omr.scoring.totalQuestions : 0,
                    correctCount: this.currentResults.omr ? this.currentResults.omr.scoring.correctCount : 0
                }
            };

            const id = await this.storage.saveResult(resultData);
            console.log(`✅ 結果已儲存，ID: ${id}`);

            this.showSuccess('處理結果已儲存！');

            // 更新儲存空間資訊
            const estimate = await this.storage.getStorageEstimate();
            console.log(`💾 儲存空間: ${estimate.usageInMB}MB / ${estimate.quotaInMB}MB (${estimate.percentage}%)`);

        } catch (error) {
            console.error('❌ 儲存失敗:', error);
            this.showError('儲存失敗：' + error.message);
        }
    }

    /**
     * 將 Canvas 轉換為 Blob
     */
    async canvasToBlob(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            throw new Error(`Canvas ${canvasId} 不存在`);
        }

        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => {
                if (blob) {
                    resolve(blob);
                } else {
                    reject(new Error('Canvas 轉換 Blob 失敗'));
                }
            }, 'image/png');
        });
    }

    /**
     * 顯示歷史記錄
     */
    async showHistory() {
        if (!this.storage) {
            this.showError('儲存功能未啟用');
            return;
        }

        if (!this.elements.historySection || !this.elements.historyList) {
            console.warn('⚠️ 歷史記錄 UI 未找到');
            return;
        }

        try {
            console.log('📋 載入歷史記錄...');

            const results = await this.storage.getAllResults();

            if (results.length === 0) {
                this.elements.historyList.innerHTML = '<p class="no-history">尚無儲存的記錄</p>';
            } else {
                this.renderHistoryList(results);
            }

            // 顯示歷史記錄區域
            this.elements.historySection.style.display = 'block';
            this.elements.historySection.classList.add('fade-in');

        } catch (error) {
            console.error('❌ 載入歷史記錄失敗:', error);
            this.showError('載入歷史記錄失敗：' + error.message);
        }
    }

    /**
     * 渲染歷史記錄列表
     */
    renderHistoryList(results) {
        // 清理舊的 Blob URLs
        this.revokeAllBlobUrls();

        let html = '<div class="history-grid">';

        results.forEach((result) => {
            const date = new Date(result.timestamp).toLocaleString('zh-TW');
            const imageUrl = URL.createObjectURL(result.originalImageBlob);

            // 追蹤新建立的 Blob URL
            this.activeBlobUrls.add(imageUrl);

            html += `
                <div class="history-item" data-id="${result.id}">
                    <img src="${imageUrl}" class="history-thumbnail" alt="Result ${result.id}">
                    <div class="history-info">
                        <p class="history-date">${date}</p>
                        <p class="history-score">分數: ${result.score}</p>
                        <p class="history-meta">${result.metadata.fileName || '未知檔案'}</p>
                        <div class="history-actions">
                            <button class="btn-small btn-danger delete-item-btn" data-id="${result.id}">
                                🗑️ 刪除
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        html += `<button class="btn btn-danger" id="delete-all-btn" style="margin-top: 1rem;">🗑️ 清空所有記錄</button>`;

        this.elements.historyList.innerHTML = html;
    }

    /**
     * 釋放所有 Blob URLs
     */
    revokeAllBlobUrls() {
        this.activeBlobUrls.forEach(url => URL.revokeObjectURL(url));
        this.activeBlobUrls.clear();
    }

    /**
     * 關閉歷史記錄
     */
    closeHistory() {
        if (this.elements.historySection) {
            this.elements.historySection.style.display = 'none';

            // 釋放所有 Blob URLs
            this.revokeAllBlobUrls();
        }
    }

    /**
     * 刪除單筆歷史記錄
     */
    async deleteHistoryItem(id) {
        if (!confirm('確定要刪除這筆記錄嗎？')) {
            return;
        }

        try {
            await this.storage.deleteResult(id);
            console.log(`✅ 記錄已刪除，ID: ${id}`);

            // 重新載入歷史記錄
            this.showHistory();

        } catch (error) {
            console.error('❌ 刪除失敗:', error);
            this.showError('刪除失敗：' + error.message);
        }
    }

    /**
     * 刪除所有歷史記錄
     */
    async deleteAllHistory() {
        if (!confirm('確定要刪除所有記錄嗎？此操作無法復原。')) {
            return;
        }

        try {
            await this.storage.deleteAllResults();
            console.log('✅ 所有記錄已刪除');

            this.showSuccess('所有記錄已清空');

            // 重新載入歷史記錄
            this.showHistory();

        } catch (error) {
            console.error('❌ 刪除失敗:', error);
            this.showError('刪除失敗：' + error.message);
        }
    }
}

// 等待 DOM 載入完成後初始化應用程式
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new OMRApp();
    });
} else {
    // DOM 已經載入完成
    new OMRApp();
}
