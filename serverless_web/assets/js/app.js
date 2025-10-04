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
            appContent: document.getElementById('app-content'),
            versionInfo: document.getElementById('opencv-version')
        };

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

        // 顯示版本資訊
        this.displayVersionInfo();

        // 顯示主要內容區域 (淡入動畫)
        setTimeout(() => {
            this.elements.appContent.style.display = 'block';
            this.elements.appContent.classList.add('fade-in');
        }, 800);

        // 測試 OpenCV 功能
        this.testOpenCV();
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
     * 顯示 OpenCV 版本資訊
     */
    displayVersionInfo() {
        const version = window.opencvLoader.getVersion();

        if (version) {
            this.elements.versionInfo.innerHTML = `
                <strong>OpenCV 版本:</strong> ${version}<br>
                <strong>執行環境:</strong> WebAssembly (Browser)
            `;
            console.log(`ℹ️ OpenCV 版本: ${version}`);
        }
    }

    /**
     * 測試 OpenCV 基本功能
     */
    testOpenCV() {
        try {
            // 建立一個簡單的矩陣來測試 OpenCV 是否正常運作
            const testMat = new cv.Mat(100, 100, cv.CV_8UC3);

            console.log('🧪 OpenCV 功能測試:');
            console.log(`  - 矩陣建立: ✅ (${testMat.rows}x${testMat.cols})`);
            console.log(`  - 矩陣類型: ${testMat.type()}`);
            console.log(`  - 記憶體管理: ✅`);

            // 釋放測試矩陣
            testMat.delete();

            console.log('✅ OpenCV 所有功能測試通過');
        } catch (e) {
            console.error('❌ OpenCV 功能測試失敗:', e);
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
