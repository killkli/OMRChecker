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

    // ==================== Stage 3: 輪廓檢測與透視校正 ====================

    /**
     * Canny 邊緣檢測
     * @param {cv.Mat} src - 來源影像（灰階）
     * @param {number} threshold1 - 第一個閾值（預設 50）
     * @param {number} threshold2 - 第二個閾值（預設 150）
     * @returns {cv.Mat} - 邊緣影像
     */
    cannyEdgeDetection(src, threshold1 = 50, threshold2 = 150) {
        const edges = new cv.Mat();
        cv.Canny(src, edges, threshold1, threshold2, 3, false);
        this.processedMats.push(edges);
        return edges;
    }

    /**
     * 查找輪廓
     * @param {cv.Mat} binary - 二值化影像
     * @returns {cv.MatVector} - 輪廓陣列
     */
    findContours(binary) {
        const contours = new cv.MatVector();
        const hierarchy = new cv.Mat();

        cv.findContours(
            binary,
            contours,
            hierarchy,
            cv.RETR_EXTERNAL,
            cv.CHAIN_APPROX_SIMPLE
        );

        hierarchy.delete();
        return contours;
    }

    /**
     * 篩選四邊形輪廓
     * @param {cv.MatVector} contours - 所有輪廓
     * @param {number} imageArea - 影像總面積
     * @param {number} minAreaRatio - 最小面積比例（預設 0.2 = 20%）
     * @returns {Array} - 四邊形輪廓陣列
     */
    filterQuadrilateralContours(contours, imageArea, minAreaRatio = 0.2) {
        const quadContours = [];
        const minArea = imageArea * minAreaRatio;

        for (let i = 0; i < contours.size(); i++) {
            const contour = contours.get(i);
            const area = cv.contourArea(contour);

            // 過濾太小的輪廓
            if (area < minArea) {
                continue;
            }

            // 使用多邊形逼近
            const peri = cv.arcLength(contour, true);
            const approx = new cv.Mat();
            cv.approxPolyDP(contour, approx, 0.02 * peri, true);

            // 檢查是否為四邊形
            if (approx.rows === 4) {
                quadContours.push({
                    contour: approx,
                    area: area
                });
            } else {
                approx.delete();
            }
        }

        // 依面積排序（由大到小）
        quadContours.sort((a, b) => b.area - a.area);

        // 返回輪廓 Mat（不包含 metadata）
        return quadContours.map(q => q.contour);
    }

    /**
     * 排序角點（左上、右上、右下、左下）
     * @param {Array} points - 四個角點 [{x, y}, ...]
     * @returns {Array} - 排序後的角點
     */
    orderCorners(points) {
        if (points.length !== 4) {
            throw new Error('必須提供 4 個角點');
        }

        // 計算每個點的 x + y 和 x - y
        const sums = points.map(p => ({ point: p, sum: p.x + p.y }));
        const diffs = points.map(p => ({ point: p, diff: p.x - p.y }));

        // 排序
        sums.sort((a, b) => a.sum - b.sum);
        diffs.sort((a, b) => a.diff - b.diff);

        // 左上：x + y 最小
        const topLeft = sums[0].point;

        // 右下：x + y 最大
        const bottomRight = sums[3].point;

        // 右上：x - y 最大
        const topRight = diffs[3].point;

        // 左下：x - y 最小
        const bottomLeft = diffs[0].point;

        return [topLeft, topRight, bottomRight, bottomLeft];
    }

    /**
     * 計算透視變換矩陣
     * @param {Array} srcPoints - 來源四個角點
     * @param {Array} dstPoints - 目標四個角點
     * @returns {cv.Mat} - 3x3 變換矩陣
     */
    getPerspectiveTransform(srcPoints, dstPoints) {
        // 將點陣列轉換為 cv.Mat
        const srcMat = cv.matFromArray(4, 1, cv.CV_32FC2,
            srcPoints.flatMap(p => [p.x, p.y])
        );

        const dstMat = cv.matFromArray(4, 1, cv.CV_32FC2,
            dstPoints.flatMap(p => [p.x, p.y])
        );

        const M = cv.getPerspectiveTransform(srcMat, dstMat);

        srcMat.delete();
        dstMat.delete();

        return M;
    }

    /**
     * 應用透視變換
     * @param {cv.Mat} src - 來源影像
     * @param {cv.Mat} M - 變換矩陣
     * @param {number} width - 輸出寬度
     * @param {number} height - 輸出高度
     * @returns {cv.Mat} - 校正後的影像
     */
    applyPerspectiveTransform(src, M, width, height) {
        const warped = new cv.Mat();
        const dsize = new cv.Size(width, height);

        cv.warpPerspective(
            src,
            warped,
            M,
            dsize,
            cv.INTER_LINEAR,
            cv.BORDER_CONSTANT,
            new cv.Scalar(255, 255, 255, 255)
        );

        this.processedMats.push(warped);
        return warped;
    }

    /**
     * 完整的透視校正流程
     * @param {cv.Mat} src - 來源影像
     * @returns {Object} - { corrected: Mat, corners: Array, visualization: Mat }
     */
    correctPerspective(src) {
        let contours = null;
        let visualization = null;
        let M = null;
        let quadContours = [];

        try {
            console.log('🔄 開始透視校正流程...');

            // 1. 預處理：灰階、模糊、二值化（這些會自動加入 processedMats）
            const gray = this.convertToGrayscale(src);
            const blurred = this.gaussianBlur(gray, 5);
            const binary = this.adaptiveThreshold(blurred);
            console.log('  ✅ 預處理完成');

            // 2. Canny 邊緣檢測
            const edges = this.cannyEdgeDetection(blurred);
            console.log('  ✅ 邊緣檢測完成');

            // 3. 查找輪廓
            contours = this.findContours(edges);
            console.log(`  ✅ 找到 ${contours.size()} 個輪廓`);

            // 4. 篩選四邊形輪廓
            const imageArea = src.rows * src.cols;
            quadContours = this.filterQuadrilateralContours(contours, imageArea);

            if (quadContours.length === 0) {
                throw new Error('未找到答案卡輪廓，請確保答案卡完整且清晰可見');
            }

            console.log(`  ✅ 找到 ${quadContours.length} 個四邊形輪廓`);

            // 5. 取得最大的四邊形（假設為答案卡）
            const paperContour = quadContours[0];

            // 6. 提取角點
            const corners = [];
            for (let i = 0; i < paperContour.rows; i++) {
                corners.push({
                    x: paperContour.data32S[i * 2],
                    y: paperContour.data32S[i * 2 + 1]
                });
            }

            console.log('  📍 檢測到的角點:', corners);

            // 7. 排序角點
            const orderedCorners = this.orderCorners(corners);
            console.log('  ✅ 角點排序完成');

            // 8. 計算輸出尺寸（A4 比例，寬度 850px）
            const outputWidth = 850;
            const outputHeight = Math.round(outputWidth * 1.414); // A4 比例

            // 9. 定義目標點（矩形）
            const dstPoints = [
                { x: 0, y: 0 },
                { x: outputWidth - 1, y: 0 },
                { x: outputWidth - 1, y: outputHeight - 1 },
                { x: 0, y: outputHeight - 1 }
            ];

            // 10. 計算透視變換矩陣
            M = this.getPerspectiveTransform(orderedCorners, dstPoints);
            console.log('  ✅ 透視變換矩陣計算完成');

            // 11. 應用透視變換
            const corrected = this.applyPerspectiveTransform(src, M, outputWidth, outputHeight);
            console.log(`  ✅ 透視校正完成 (${outputWidth}x${outputHeight})`);

            // 12. 建立視覺化（在原圖上標記角點）
            visualization = src.clone();
            for (let i = 0; i < orderedCorners.length; i++) {
                const corner = orderedCorners[i];
                const nextCorner = orderedCorners[(i + 1) % 4];

                // 畫圓標記角點
                cv.circle(
                    visualization,
                    new cv.Point(corner.x, corner.y),
                    10,
                    new cv.Scalar(0, 255, 0, 255),
                    -1
                );

                // 畫線連接角點
                cv.line(
                    visualization,
                    new cv.Point(corner.x, corner.y),
                    new cv.Point(nextCorner.x, nextCorner.y),
                    new cv.Scalar(255, 0, 0, 255),
                    3
                );
            }

            this.processedMats.push(visualization);

            console.log('✅ 透視校正流程完成！');

            return {
                corrected: corrected,
                corners: orderedCorners,
                visualization: visualization
            };

        } finally {
            // 清理那些不在 processedMats 中的資源
            if (contours) contours.delete();
            if (M) M.delete();

            // 清理四邊形輪廓陣列
            quadContours.forEach(c => {
                if (c && !c.isDeleted()) c.delete();
            });

            // 如果 visualization 建立失敗，需要清理
            if (visualization && !this.processedMats.includes(visualization)) {
                visualization.delete();
            }
        }
    }
}
