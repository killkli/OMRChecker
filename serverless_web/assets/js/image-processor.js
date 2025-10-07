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
                    resolve(true);
                    return;
                }

                // 檢查 PNG 簽名 (89 50 4E 47)
                if (arr[0] === ImageProcessor.MAGIC_NUMBERS.PNG[0] &&
                    arr[1] === ImageProcessor.MAGIC_NUMBERS.PNG[1] &&
                    arr[2] === ImageProcessor.MAGIC_NUMBERS.PNG[2] &&
                    arr[3] === ImageProcessor.MAGIC_NUMBERS.PNG[3]) {
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

    // ==================== Stage 4: 答案標記檢測與解析 ====================

    /**
     * 載入並解析模板 JSON 檔案
     * @param {string} templateUrl - 模板檔案 URL
     * @returns {Promise<Object>} - 模板物件
     */
    async loadTemplate(templateUrl) {
        try {
            const response = await fetch(templateUrl);
            if (!response.ok) {
                throw new Error(`無法載入模板: ${response.statusText}`);
            }
            const template = await response.json();
            console.log('✅ 模板載入成功:', template.name);
            return template;
        } catch (error) {
            console.error('❌ 模板載入失敗:', error);
            throw new Error(`模板載入失敗: ${error.message}`);
        }
    }

    /**
     * 根據模板產生所有標記的預期位置
     * @param {Object} template - 模板物件
     * @returns {Array} - 標記位置陣列 [{questionNo, option, x, y, diameter}, ...]
     */
    generateBubblePositions(template) {
        const positions = [];
        const bubbleDiameter = template.bubbles.diameter;

        template.layout.regions.forEach(region => {
            const { origin, questions, options } = region;

            for (let q = questions.start; q <= questions.end; q++) {
                // 計算當前題號的 Y 座標（垂直方向）
                const questionIndex = q - questions.start;
                const questionY = origin.y + (questionIndex * questions.gap);

                // 為每個選項產生標記位置
                options.values.forEach((optionValue, optionIndex) => {
                    const optionX = origin.x + (optionIndex * options.gap);

                    positions.push({
                        questionNo: q,
                        option: optionValue,
                        x: optionX,
                        y: questionY,
                        diameter: bubbleDiameter,
                        regionId: region.id
                    });
                });
            }
        });

        console.log(`  ✅ 產生 ${positions.length} 個標記位置`);
        return positions;
    }

    /**
     * 檢測圓形標記（使用 HoughCircles）
     * @param {cv.Mat} binary - 二值化影像
     * @param {number} minRadius - 最小半徑
     * @param {number} maxRadius - 最大半徑
     * @returns {Array} - 檢測到的圓形 [{x, y, radius}, ...]
     */
    detectCircles(binary, minRadius = 10, maxRadius = 25) {
        const circles = new cv.Mat();
        const inverted = new cv.Mat();

        try {
            // 反轉影像（HoughCircles 需要黑底白圓）
            cv.bitwise_not(binary, inverted);

            // Hough Circle Transform
            cv.HoughCircles(
                inverted,
                circles,
                cv.HOUGH_GRADIENT,
                1,              // dp: 累加器解析度與影像解析度的比值
                minRadius * 2,  // minDist: 圓心之間的最小距離
                100,            // param1: Canny 邊緣檢測的高閾值
                30,             // param2: 累加器閾值（越小檢測到越多圓）
                minRadius,      // minRadius
                maxRadius       // maxRadius
            );

            // 轉換為 JavaScript 陣列
            const detectedCircles = [];
            for (let i = 0; i < circles.cols; i++) {
                detectedCircles.push({
                    x: circles.data32F[i * 3],
                    y: circles.data32F[i * 3 + 1],
                    radius: circles.data32F[i * 3 + 2]
                });
            }

            console.log(`  ✅ 檢測到 ${detectedCircles.length} 個圓形`);
            return detectedCircles;

        } finally {
            circles.delete();
            inverted.delete();
        }
    }

    /**
     * 檢測矩形標記（使用輪廓檢測）
     * @param {cv.Mat} binary - 二值化影像
     * @param {number} minArea - 最小面積
     * @param {number} maxArea - 最大面積
     * @returns {Array} - 檢測到的矩形 [{x, y, width, height}, ...]
     */
    detectRectangles(binary, minArea = 400, maxArea = 2000) {
        const contours = this.findContours(binary);
        const rectangles = [];

        for (let i = 0; i < contours.size(); i++) {
            const contour = contours.get(i);
            const area = cv.contourArea(contour);

            if (area < minArea || area > maxArea) {
                continue;
            }

            // 計算邊界矩形
            const rect = cv.boundingRect(contour);

            // 檢查是否接近正方形（寬高比）
            const aspectRatio = rect.width / rect.height;
            if (aspectRatio > 0.7 && aspectRatio < 1.3) {
                rectangles.push({
                    x: rect.x + rect.width / 2,  // 中心點 X
                    y: rect.y + rect.height / 2, // 中心點 Y
                    width: rect.width,
                    height: rect.height
                });
            }
        }

        contours.delete();
        console.log(`  ✅ 檢測到 ${rectangles.length} 個矩形標記`);
        return rectangles;
    }

    /**
     * 匹配檢測到的標記與模板位置
     * @param {Array} detectedMarkers - 檢測到的標記 [{x, y, ...}, ...]
     * @param {Array} templatePositions - 模板定義的位置
     * @param {number} tolerance - 容許誤差（像素）
     * @returns {Array} - 匹配結果 [{questionNo, option, x, y, matched: true/false}, ...]
     */
    matchBubbles(detectedMarkers, templatePositions, tolerance = 15) {
        const matched = [];

        templatePositions.forEach(templatePos => {
            // 尋找最近的檢測標記
            let closestMarker = null;
            let minDistance = Infinity;

            detectedMarkers.forEach(marker => {
                const distance = Math.sqrt(
                    Math.pow(marker.x - templatePos.x, 2) +
                    Math.pow(marker.y - templatePos.y, 2)
                );

                if (distance < minDistance) {
                    minDistance = distance;
                    closestMarker = marker;
                }
            });

            // 如果距離在容許範圍內，視為匹配
            if (closestMarker && minDistance <= tolerance) {
                matched.push({
                    questionNo: templatePos.questionNo,
                    option: templatePos.option,
                    x: Math.round(closestMarker.x),
                    y: Math.round(closestMarker.y),
                    matched: true,
                    distance: Math.round(minDistance)
                });
            } else {
                // 未匹配到，使用模板位置
                matched.push({
                    questionNo: templatePos.questionNo,
                    option: templatePos.option,
                    x: templatePos.x,
                    y: templatePos.y,
                    matched: false,
                    distance: null
                });
            }
        });

        const matchedCount = matched.filter(m => m.matched).length;
        const matchRate = (matchedCount / matched.length * 100).toFixed(1);
        console.log(`  ✅ 標記匹配完成: ${matchedCount}/${matched.length} (${matchRate}%)`);

        return matched;
    }

    /**
     * 計算標記的填充率
     * @param {cv.Mat} binary - 二值化影像
     * @param {number} x - 標記中心 X 座標
     * @param {number} y - 標記中心 Y 座標
     * @param {number} diameter - 標記直徑
     * @returns {number} - 填充率 (0.0 ~ 1.0)
     */
    calculateFillRatio(binary, x, y, diameter) {
        const radius = Math.floor(diameter / 2);
        const roiSize = diameter;

        // 確保 ROI 在影像範圍內
        const x1 = Math.max(0, x - radius);
        const y1 = Math.max(0, y - radius);
        const x2 = Math.min(binary.cols, x + radius);
        const y2 = Math.min(binary.rows, y + radius);

        if (x2 <= x1 || y2 <= y1) {
            return 0;
        }

        // 提取 ROI
        const roi = binary.roi(new cv.Rect(x1, y1, x2 - x1, y2 - y1));

        try {
            // 計算黑色像素數量（在二值化影像中，黑色 = 0）
            const totalPixels = roi.rows * roi.cols;

            // 使用 OpenCV 原生函數計算非零像素（白色像素）
            const whitePixels = cv.countNonZero(roi);
            const blackPixels = totalPixels - whitePixels;

            const fillRatio = blackPixels / totalPixels;
            return fillRatio;
        } finally {
            // 確保 ROI 記憶體被釋放
            roi.delete();
        }
    }

    /**
     * 判斷標記是否已填塗
     * @param {cv.Mat} binary - 二值化影像
     * @param {Array} bubblePositions - 標記位置陣列
     * @param {number} threshold - 填充閾值（預設 0.4 = 40%）
     * @returns {Array} - 帶有填充狀態的標記 [{...bubble, fillRatio, isFilled}, ...]
     */
    detectFilledBubbles(binary, bubblePositions, threshold = 0.4) {
        const results = [];

        bubblePositions.forEach(bubble => {
            const fillRatio = this.calculateFillRatio(
                binary,
                bubble.x,
                bubble.y,
                bubble.diameter
            );

            results.push({
                ...bubble,
                fillRatio: parseFloat(fillRatio.toFixed(3)),
                isFilled: fillRatio >= threshold
            });
        });

        const filledCount = results.filter(b => b.isFilled).length;
        console.log(`  ✅ 檢測填充狀態: ${filledCount}/${results.length} 個標記已填塗`);

        return results;
    }

    /**
     * 解析答案（根據填充狀態）
     * @param {Array} filledBubbles - 帶有填充狀態的標記
     * @returns {Object} - { questionNo: [selectedOptions], ... }
     */
    parseAnswers(filledBubbles) {
        const answers = {};

        filledBubbles.forEach(bubble => {
            if (bubble.isFilled) {
                if (!answers[bubble.questionNo]) {
                    answers[bubble.questionNo] = [];
                }
                answers[bubble.questionNo].push(bubble.option);
            }
        });

        // 對每題的答案排序（確保一致性）
        Object.keys(answers).forEach(questionNo => {
            answers[questionNo].sort();
        });

        console.log(`  ✅ 解析答案完成: ${Object.keys(answers).length} 題已作答`);
        return answers;
    }

    /**
     * 計算分數
     * @param {Object} studentAnswers - 學生答案 { questionNo: [options], ... }
     * @param {Object} answerKey - 標準答案 { questionNo: correctOption, ... }
     * @param {number} pointsPerQuestion - 每題分數
     * @returns {Object} - 評分結果
     */
    calculateScore(studentAnswers, answerKey, pointsPerQuestion = 5) {
        let correctCount = 0;
        let incorrectCount = 0;
        let unansweredCount = 0;
        const details = {};

        const totalQuestions = Object.keys(answerKey).length;

        for (let q = 1; q <= totalQuestions; q++) {
            const questionNo = q.toString();
            const correctAnswer = answerKey[questionNo];
            const studentAnswer = studentAnswers[questionNo];

            if (!studentAnswer || studentAnswer.length === 0) {
                // 未作答
                unansweredCount++;
                details[questionNo] = {
                    correct: correctAnswer,
                    student: null,
                    isCorrect: false,
                    status: 'unanswered'
                };
            } else if (studentAnswer.length === 1 && studentAnswer[0] === correctAnswer) {
                // 答對（單選）
                correctCount++;
                details[questionNo] = {
                    correct: correctAnswer,
                    student: studentAnswer[0],
                    isCorrect: true,
                    status: 'correct'
                };
            } else {
                // 答錯或複選
                incorrectCount++;
                details[questionNo] = {
                    correct: correctAnswer,
                    student: studentAnswer.length > 1 ? studentAnswer.join(',') : studentAnswer[0],
                    isCorrect: false,
                    status: studentAnswer.length > 1 ? 'multiple' : 'incorrect'
                };
            }
        }

        const score = correctCount * pointsPerQuestion;
        const totalPoints = totalQuestions * pointsPerQuestion;
        const percentage = (score / totalPoints * 100).toFixed(1);

        console.log(`  ✅ 評分完成: ${correctCount}/${totalQuestions} 題正確，得分 ${score}/${totalPoints} (${percentage}%)`);

        return {
            score: score,
            totalPoints: totalPoints,
            percentage: parseFloat(percentage),
            correctCount: correctCount,
            incorrectCount: incorrectCount,
            unansweredCount: unansweredCount,
            totalQuestions: totalQuestions,
            details: details
        };
    }

    /**
     * 完整的 OMR 答案檢測流程
     * @param {cv.Mat} correctedImage - 校正後的答案卡影像
     * @param {Object} template - 模板物件
     * @returns {Object} - 檢測結果
     */
    async detectAndParseAnswers(correctedImage, template) {
        let binary = null;
        let visualization = null;

        try {
            console.log('🔄 開始答案檢測流程...');

            // 1. 預處理：灰階、模糊、二值化
            const gray = this.convertToGrayscale(correctedImage);
            const blurred = this.gaussianBlur(gray, 5);
            binary = this.adaptiveThreshold(blurred);
            console.log('  ✅ 預處理完成');

            // 2. 產生標記位置
            const bubblePositions = this.generateBubblePositions(template);

            // 3. 檢測標記填充狀態（直接使用模板位置，不進行圓形檢測）
            const filledBubbles = this.detectFilledBubbles(
                binary,
                bubblePositions,
                template.bubbles.fillThreshold
            );

            // 4. 解析答案
            const studentAnswers = this.parseAnswers(filledBubbles);

            // 5. 計算分數
            const scoringResult = this.calculateScore(
                studentAnswers,
                template.answerKey,
                template.scoring.pointsPerQuestion
            );

            // 6. 建立視覺化（在校正後的影像上標記答案）
            visualization = correctedImage.clone();
            this.visualizeAnswers(visualization, filledBubbles, scoringResult.details);
            this.processedMats.push(visualization);

            console.log('✅ 答案檢測流程完成！');

            return {
                bubbles: filledBubbles,
                answers: studentAnswers,
                scoring: scoringResult,
                visualization: visualization
            };

        } catch (error) {
            console.error('❌ 答案檢測失敗:', error);
            throw error;
        }
    }

    /**
     * 在影像上視覺化答案
     * @param {cv.Mat} img - 影像
     * @param {Array} bubbles - 標記陣列
     * @param {Object} details - 答題詳情
     */
    visualizeAnswers(img, bubbles, details) {
        bubbles.forEach(bubble => {
            const questionDetail = details[bubble.questionNo.toString()];
            let color;

            if (bubble.isFilled) {
                // 判斷是否答對
                if (questionDetail && questionDetail.isCorrect) {
                    color = new cv.Scalar(0, 255, 0, 255);  // 綠色：答對
                } else {
                    color = new cv.Scalar(255, 0, 0, 255);  // 紅色：答錯
                }

                // 畫實心圓
                cv.circle(
                    img,
                    new cv.Point(bubble.x, bubble.y),
                    Math.floor(bubble.diameter / 2),
                    color,
                    2
                );
            } else {
                // 未填塗的標記畫空心圓（灰色）
                color = new cv.Scalar(128, 128, 128, 255);
                cv.circle(
                    img,
                    new cv.Point(bubble.x, bubble.y),
                    Math.floor(bubble.diameter / 2),
                    color,
                    1
                );
            }
        });

        console.log('  ✅ 答案視覺化完成');
    }
}
