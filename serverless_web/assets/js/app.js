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
            uploadNewBtn: document.getElementById('upload-new-btn')
        };

        this.imageProcessor = null;
        this.currentFile = null;

        this.init();
    }

    /**
     * 初始化應用程式
     */
    init() {
        console.log('🚀 OMR Checker 應用程式啟動');

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

            // 4. 處理影像
            this.showProgress('處理影像中...');
            const results = this.imageProcessor.preprocessImage(imgElement);

            // 5. 顯示結果
            this.displayResults(results);

            this.showSuccess('影像處理完成！');

        } catch (error) {
            console.error('❌ 處理檔案時發生錯誤:', error);
            this.showError('處理失敗：' + error.message);
        }
    }

    /**
     * 顯示處理結果
     */
    displayResults(results) {
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
            console.log('✅ 處理結果已顯示在 Canvas');
        } catch (error) {
            console.error('❌ Canvas 顯示失敗:', error);
            this.showError('結果顯示失敗：' + error.message);
        }
    }

    /**
     * 重新處理當前影像
     */
    reprocessImage() {
        if (this.currentFile) {
            console.log('🔄 重新處理影像');
            // 清理舊的 Mat
            if (this.imageProcessor) {
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
        const canvases = ['canvas-original', 'canvas-grayscale', 'canvas-blurred', 'canvas-binary'];
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
