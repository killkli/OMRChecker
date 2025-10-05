/**
 * OMR Checker - Export Module
 * 負責將處理結果匯出為 CSV 或 JSON 格式
 */

class OMRExporter {
    /**
     * Escape special characters for CSV format
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    static escapeCSV(str) {
        if (typeof str !== 'string') return str;
        // Escape double quotes by doubling them
        return str.replace(/"/g, '""');
    }

    /**
     * 匯出單筆結果為 CSV 格式
     * @param {Object} result - 處理結果物件
     * @param {Object} result.omr - OMR 檢測結果
     * @param {Object} result.omr.answers - 學生答案 { 題號: [答案陣列] }
     * @param {Object} result.omr.scoring - 評分結果
     * @param {Object} result.omr.scoring.details - 詳細評分 { 題號: {student, correct, isCorrect, status} }
     * @param {Object} template - 使用的模板
     * @param {String} fileName - 檔案名稱（可選）
     * @returns {void}
     */
    static exportToCSV(result, template, fileName = 'omr-result.csv') {
        if (!result || !result.omr) {
            throw new Error('無效的結果資料');
        }

        const { scoring } = result.omr;

        // 建立 CSV 內容
        let csvContent = '\uFEFF'; // UTF-8 BOM for Excel compatibility

        // Header
        csvContent += '題號,學生答案,正確答案,是否正確\n';

        // 詳細答題情況
        const questionNumbers = Object.keys(scoring.details).sort((a, b) => parseInt(a) - parseInt(b));

        questionNumbers.forEach(questionNo => {
            const detail = scoring.details[questionNo];
            const studentAnswer = this.escapeCSV(detail.student || '(未作答)');
            const correctAnswer = this.escapeCSV(detail.correct);
            const isCorrect = detail.isCorrect ? '✓' : '✗';

            csvContent += `${questionNo},"${studentAnswer}","${correctAnswer}",${isCorrect}\n`;
        });

        // 總分資訊
        csvContent += '\n';
        csvContent += `總分,${scoring.score},${scoring.totalPoints},${scoring.percentage}%\n`;
        csvContent += `答對,${scoring.correctCount},題,\n`;
        csvContent += `答錯,${scoring.incorrectCount},題,\n`;
        csvContent += `未作答,${scoring.unansweredCount},題,\n`;

        // 模板資訊
        if (template) {
            csvContent += '\n';
            csvContent += `使用模板,"${template.name}",,\n`;
        }

        // 下載檔案
        this.downloadFile(csvContent, fileName, 'text/csv;charset=utf-8;');
    }

    /**
     * 匯出單筆結果為 JSON 格式
     * @param {Object} result - 處理結果物件
     * @param {Object} template - 使用的模板
     * @param {Object} metadata - 額外的中繼資料（可選）
     * @param {String} fileName - 檔案名稱（可選）
     * @returns {void}
     */
    static exportToJSON(result, template, metadata = {}, fileName = 'omr-result.json') {
        if (!result || !result.omr) {
            throw new Error('無效的結果資料');
        }

        const { answers, scoring } = result.omr;

        // 建立 JSON 物件
        const jsonData = {
            timestamp: new Date().toISOString(),
            templateName: template ? template.name : 'unknown',
            answers: answers,
            scoring: {
                score: scoring.score,
                totalPoints: scoring.totalPoints,
                percentage: scoring.percentage,
                correctCount: scoring.correctCount,
                incorrectCount: scoring.incorrectCount,
                unansweredCount: scoring.unansweredCount,
                details: scoring.details
            },
            metadata: metadata
        };

        // 轉換為 JSON 字串（格式化）
        const jsonContent = JSON.stringify(jsonData, null, 2);

        // 下載檔案
        this.downloadFile(jsonContent, fileName, 'application/json;charset=utf-8;');
    }

    /**
     * 批次匯出多筆結果為 JSON 格式
     * @param {Array} results - 結果陣列
     * @param {String} fileName - 檔案名稱（可選）
     * @returns {void}
     */
    static exportBatchToJSON(results, fileName = 'omr-results-batch.json') {
        if (!Array.isArray(results) || results.length === 0) {
            throw new Error('無效的結果陣列');
        }

        // 建立批次 JSON 物件
        const batchData = {
            exportDate: new Date().toISOString(),
            totalRecords: results.length,
            results: results.map((result, index) => ({
                id: result.id || index + 1,
                timestamp: result.timestamp ? result.timestamp.toISOString() : null,
                templateName: result.templateName,
                answers: result.answers,
                score: result.score,
                metadata: result.metadata
            }))
        };

        // 轉換為 JSON 字串（格式化）
        const jsonContent = JSON.stringify(batchData, null, 2);

        // 下載檔案
        this.downloadFile(jsonContent, fileName, 'application/json;charset=utf-8;');
    }

    /**
     * 批次匯出多筆結果為 CSV 格式（摘要）
     * @param {Array} results - 結果陣列
     * @param {String} fileName - 檔案名稱（可選）
     * @returns {void}
     */
    static exportBatchToCSV(results, fileName = 'omr-results-batch.csv') {
        if (!Array.isArray(results) || results.length === 0) {
            throw new Error('無效的結果陣列');
        }

        // 建立 CSV 內容
        let csvContent = '\uFEFF'; // UTF-8 BOM for Excel compatibility

        // Header
        csvContent += 'ID,時間,模板,分數,檔案名稱\n';

        // 資料行
        results.forEach(result => {
            const id = result.id || '';
            const timestamp = result.timestamp ? new Date(result.timestamp).toLocaleString('zh-TW') : '';
            const templateName = this.escapeCSV(result.templateName || 'unknown');
            const score = result.score || 0;
            const resultFileName = this.escapeCSV(result.metadata?.fileName || 'unknown');

            csvContent += `${id},"${this.escapeCSV(timestamp)}","${templateName}",${score},"${resultFileName}"\n`;
        });

        // 下載檔案
        this.downloadFile(csvContent, fileName, 'text/csv;charset=utf-8;');
    }

    /**
     * 觸發檔案下載
     * @param {String} content - 檔案內容
     * @param {String} fileName - 檔案名稱
     * @param {String} mimeType - MIME 類型
     * @returns {void}
     */
    static downloadFile(content, fileName, mimeType) {
        try {
            // 建立 Blob
            const blob = new Blob([content], { type: mimeType });

            // 建立下載連結
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = fileName;

            // 觸發下載
            document.body.appendChild(link);
            link.click();

            // 清理
            document.body.removeChild(link);

            // 延遲釋放 URL，確保下載完成
            setTimeout(() => {
                URL.revokeObjectURL(url);
            }, 100);

            console.log(`✅ 檔案已下載: ${fileName}`);
        } catch (error) {
            console.error('❌ 下載檔案失敗:', error);
            throw new Error('檔案下載失敗: ' + error.message);
        }
    }

    /**
     * 生成安全的檔案名稱（移除特殊字元）
     * @param {String} baseName - 基礎名稱
     * @param {String} extension - 副檔名
     * @returns {String} 安全的檔案名稱
     */
    static generateSafeFileName(baseName, extension) {
        // 移除特殊字元，保留中文、英文、數字、底線、連字號
        const safeName = baseName.replace(/[^a-zA-Z0-9_\u4e00-\u9fa5-]/g, '_');

        // 生成時間戳記（包含毫秒）
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_');

        // 生成隨機後綴以確保唯一性
        const random = Math.random().toString(36).substring(2, 6);

        return `${safeName}_${timestamp}_${random}.${extension}`;
    }
}

// 匯出供其他模組使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OMRExporter;
}
