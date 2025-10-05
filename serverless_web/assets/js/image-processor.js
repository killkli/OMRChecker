/**
 * OMR 影像處理器
 * 負責所有 OpenCV 相關的影像處理操作
 */

class ImageProcessor {
    // 檔案驗證常數
    static MAX_FILE_SIZE = 10 * 1024 * 1024;  // 10MB
    static ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/jpg'];
    static ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png'];

    // Magic Number 常數（檔案簽名）
    static MAGIC_NUMBERS = {
        JPEG: [0xFF, 0xD8, 0xFF],
        PNG: [0x89, 0x50, 0x4E, 0x47]
    };

    constructor() {
        this.currentImage = null;  // 目前載入的影像
        this.processedMats = [];   // 追蹤所有建立的 Mat，用於記憶體管理
    }

    /**
     * 從檔案載入影像
     * @param {File} file - 檔案物件
     * @returns {Promise<HTMLImageElement>}
     */
    async loadImageFromFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (e) => {
                const img = new Image();

                img.onload = () => {
                    this.currentImage = img;
                    resolve(img);
                };

                img.onerror = () => {
                    reject(new Error('影像載入失敗'));
                };

                img.src = e.target.result;
            };

            reader.onerror = () => {
                reject(new Error('檔案讀取失敗'));
            };

            reader.readAsDataURL(file);
        });
    }

    /**
     * 驗證上傳的檔案
     * @param {File} file
     * @returns {boolean}
     */
    validateFile(file) {
        // 檢查檔案是否存在
        if (!file) {
            console.error('❌ 沒有選擇檔案');
            return false;
        }

        // 檢查 MIME type
        if (!ImageProcessor.ALLOWED_MIME_TYPES.includes(file.type)) {
            console.error('❌ 不支援的檔案類型:', file.type);
            return false;
        }

        // 檢查檔案大小
        if (file.size > ImageProcessor.MAX_FILE_SIZE) {
            console.error('❌ 檔案大小超過限制:', (file.size / 1024 / 1024).toFixed(2), 'MB');
            return false;
        }

        // 檢查副檔名
        const fileName = file.name.toLowerCase();
        const hasValidExtension = ImageProcessor.ALLOWED_EXTENSIONS.some(ext =>
            fileName.endsWith(ext)
        );

        if (!hasValidExtension) {
            console.error('❌ 不支援的檔案副檔名:', fileName);
            return false;
        }

        return true;
    }

    /**
     * 驗證檔案簽名（Magic Number）
     * @param {File} file
     * @returns {Promise<boolean>}
     */
    async validateFileSignature(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (e) => {
                const arr = new Uint8Array(e.target.result);

                // 檢查 JPEG 簽名 (FF D8 FF)
                if (arr[0] === ImageProcessor.MAGIC_NUMBERS.JPEG[0] &&
                    arr[1] === ImageProcessor.MAGIC_NUMBERS.JPEG[1] &&
                    arr[2] === ImageProcessor.MAGIC_NUMBERS.JPEG[2]) {
                    console.log('✅ 驗證通過: JPEG 檔案');
                    resolve(true);
                    return;
                }

                // 檢查 PNG 簽名 (89 50 4E 47)
                if (arr[0] === ImageProcessor.MAGIC_NUMBERS.PNG[0] &&
                    arr[1] === ImageProcessor.MAGIC_NUMBERS.PNG[1] &&
                    arr[2] === ImageProcessor.MAGIC_NUMBERS.PNG[2] &&
                    arr[3] === ImageProcessor.MAGIC_NUMBERS.PNG[3]) {
                    console.log('✅ 驗證通過: PNG 檔案');
                    resolve(true);
                    return;
                }

                console.error('❌ 檔案簽名驗證失敗');
                resolve(false);
            };

            reader.onerror = () => {
                reject(new Error('檔案簽名讀取失敗'));
            };

            // 只讀取前 4 bytes
            reader.readAsArrayBuffer(file.slice(0, 4));
        });
    }

    /**
     * 將 Image 元素轉換為 cv.Mat
     * @param {HTMLImageElement} imgElement
     * @returns {cv.Mat}
     */
    imageToMat(imgElement) {
        const mat = cv.imread(imgElement);
        this.processedMats.push(mat);
        return mat;
    }

    /**
     * 灰階轉換
     * @param {cv.Mat} src - 來源影像
     * @returns {cv.Mat} - 灰階影像
     */
    convertToGrayscale(src) {
        const gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY, 0);
        this.processedMats.push(gray);
        return gray;
    }

    /**
     * 高斯模糊降噪
     * @param {cv.Mat} src - 來源影像
     * @param {number} kernelSize - 核心大小（預設 5）
     * @returns {cv.Mat} - 模糊後的影像
     */
    gaussianBlur(src, kernelSize = 5) {
        const blurred = new cv.Mat();
        const ksize = new cv.Size(kernelSize, kernelSize);
        cv.GaussianBlur(src, blurred, ksize, 0, 0, cv.BORDER_DEFAULT);
        this.processedMats.push(blurred);
        return blurred;
    }

    /**
     * 自適應二值化
     * @param {cv.Mat} src - 來源影像（必須是灰階）
     * @param {number} blockSize - 區塊大小（預設 11）
     * @param {number} C - 常數（預設 2）
     * @returns {cv.Mat} - 二值化影像
     */
    adaptiveThreshold(src, blockSize = 11, C = 2) {
        const binary = new cv.Mat();
        cv.adaptiveThreshold(
            src,
            binary,
            255,
            cv.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv.THRESH_BINARY,
            blockSize,
            C
        );
        this.processedMats.push(binary);
        return binary;
    }

    /**
     * 完整的預處理流程
     * @param {HTMLImageElement} imgElement
     * @returns {Object} - 包含所有處理步驟的結果
     */
    preprocessImage(imgElement) {
        const results = {};

        try {
            console.log('🔄 開始影像預處理流程...');

            // 1. 讀取原始影像
            results.original = this.imageToMat(imgElement);
            console.log(`  ✅ 原始影像: ${results.original.cols}x${results.original.rows}`);

            // 2. 灰階轉換
            results.grayscale = this.convertToGrayscale(results.original);
            console.log('  ✅ 灰階轉換完成');

            // 3. 高斯模糊
            results.blurred = this.gaussianBlur(results.grayscale);
            console.log('  ✅ 高斯模糊完成');

            // 4. 自適應二值化
            results.binary = this.adaptiveThreshold(results.blurred);
            console.log('  ✅ 二值化完成');

            console.log('✅ 影像預處理流程完成！');

            return results;

        } catch (error) {
            console.error('❌ 影像處理失敗:', error);
            this.cleanup();
            throw error;
        }
    }

    /**
     * 清理所有建立的 Mat（記憶體管理）
     */
    cleanup() {
        console.log(`🧹 清理記憶體: 釋放 ${this.processedMats.length} 個 Mat 物件`);

        this.processedMats.forEach(mat => {
            if (mat && !mat.isDeleted()) {
                try {
                    mat.delete();
                } catch (e) {
                    console.warn('⚠️ Mat 刪除失敗:', e);
                }
            }
        });

        this.processedMats = [];
        this.currentImage = null;
    }

    /**
     * 取得目前載入的影像資訊
     * @returns {Object|null}
     */
    getImageInfo() {
        if (!this.currentImage) {
            return null;
        }

        return {
            width: this.currentImage.width,
            height: this.currentImage.height,
            aspectRatio: (this.currentImage.width / this.currentImage.height).toFixed(2)
        };
    }
}
