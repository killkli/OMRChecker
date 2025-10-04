/**
 * OpenCV.js 載入器
 * 負責管理 OpenCV.js 的載入狀態並提供回調機制
 */

class OpenCVLoader {
    constructor() {
        this.isReady = false;
        this.loadStartTime = Date.now();
        this.callbacks = {
            onReady: [],
            onProgress: [],
            onError: []
        };

        // 模擬載入進度 (因為 OpenCV.js 不提供實際進度)
        this.simulateProgress();
    }

    /**
     * 模擬載入進度
     * 由於 OpenCV.js 沒有提供實際載入進度,我們模擬一個進度條
     */
    simulateProgress() {
        let progress = 0;
        const interval = setInterval(() => {
            if (this.isReady) {
                progress = 100;
                this.notifyProgress(progress);
                clearInterval(interval);
                return;
            }

            // 模擬非線性進度增長 (前期快、後期慢)
            if (progress < 30) {
                progress += Math.random() * 5;
            } else if (progress < 60) {
                progress += Math.random() * 3;
            } else if (progress < 85) {
                progress += Math.random() * 2;
            } else {
                progress += Math.random() * 0.5;
            }

            progress = Math.min(progress, 90); // 最多到 90%,等待真正就緒
            this.notifyProgress(progress);
        }, 200);

        // 超時處理 (15 秒)
        setTimeout(() => {
            if (!this.isReady) {
                clearInterval(interval);
                this.notifyError(new Error('OpenCV.js 載入超時'));
            }
        }, 15000);
    }

    /**
     * OpenCV.js 載入完成回調 (由 Module.onRuntimeInitialized 呼叫)
     */
    onOpenCVReady() {
        this.isReady = true;
        const loadTime = Date.now() - this.loadStartTime;

        console.log(`✅ OpenCV.js 載入完成 (耗時: ${(loadTime / 1000).toFixed(2)} 秒)`);

        // 獲取版本資訊
        try {
            const buildInfo = cv.getBuildInformation();
            console.log('OpenCV 版本資訊:', buildInfo);
        } catch (e) {
            console.warn('無法取得 OpenCV 版本資訊:', e);
        }

        // 通知進度完成
        this.notifyProgress(100);

        // 執行所有就緒回調
        this.callbacks.onReady.forEach(callback => {
            try {
                callback();
            } catch (e) {
                console.error('OpenCV 就緒回調執行錯誤:', e);
            }
        });

        // 清空回調列表
        this.callbacks.onReady = [];
    }

    /**
     * 檢查 OpenCV.js 是否已就緒
     */
    checkReady() {
        return this.isReady;
    }

    /**
     * 註冊就緒回調
     * @param {Function} callback - 當 OpenCV.js 就緒時執行的回調
     */
    onReady(callback) {
        if (typeof callback !== 'function') {
            console.error('onReady 需要一個函數作為參數');
            return;
        }

        if (this.isReady) {
            // 如果已經就緒,立即執行
            callback();
        } else {
            // 否則加入等待列表
            this.callbacks.onReady.push(callback);
        }
    }

    /**
     * 註冊進度回調
     * @param {Function} callback - 載入進度變化時執行的回調 (參數: percent)
     */
    onProgress(callback) {
        if (typeof callback !== 'function') {
            console.error('onProgress 需要一個函數作為參數');
            return;
        }
        this.callbacks.onProgress.push(callback);
    }

    /**
     * 註冊錯誤回調
     * @param {Function} callback - 載入錯誤時執行的回調 (參數: error)
     */
    onError(callback) {
        if (typeof callback !== 'function') {
            console.error('onError 需要一個函數作為參數');
            return;
        }
        this.callbacks.onError.push(callback);
    }

    /**
     * 通知進度更新
     * @param {Number} percent - 進度百分比 (0-100)
     */
    notifyProgress(percent) {
        this.callbacks.onProgress.forEach(callback => {
            try {
                callback(percent);
            } catch (e) {
                console.error('進度回調執行錯誤:', e);
            }
        });
    }

    /**
     * 通知錯誤
     * @param {Error} error - 錯誤物件
     */
    notifyError(error) {
        console.error('OpenCV.js 載入錯誤:', error);

        this.callbacks.onError.forEach(callback => {
            try {
                callback(error);
            } catch (e) {
                console.error('錯誤回調執行錯誤:', e);
            }
        });
    }

    /**
     * 獲取 OpenCV 版本資訊
     * @returns {String|null} - 版本資訊字串,若未就緒則返回 null
     */
    getVersion() {
        if (!this.isReady) {
            return null;
        }

        try {
            const buildInfo = cv.getBuildInformation();
            // 從 build information 中提取版本號
            const versionMatch = buildInfo.match(/Version:\s*([0-9.]+)/);
            return versionMatch ? versionMatch[1] : 'Unknown';
        } catch (e) {
            console.error('取得版本失敗:', e);
            return null;
        }
    }
}

// 建立全域實例
window.opencvLoader = new OpenCVLoader();
