/**
 * OMR Checker - IndexedDB Storage Module
 * 負責瀏覽器端資料持久化，儲存處理結果和模板
 */

class OMRStorage {
    // 資料庫配置常數
    DB_NAME = 'OMRCheckerDB';
    DB_VERSION = 1;

    // Object Store 名稱
    STORE_RESULTS = 'results';
    STORE_TEMPLATES = 'templates';

    constructor() {
        this.db = null;
        this.isInitialized = false;
    }

    /**
     * 初始化資料庫
     * @returns {Promise<void>}
     */
    async init() {
        if (this.isInitialized && this.db) {
            return;
        }

        // 檢查瀏覽器是否支援 IndexedDB
        if (!window.indexedDB) {
            throw new Error('瀏覽器不支援 IndexedDB');
        }

        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

            // 資料庫升級（建立或更新 schema）
            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // 建立 results object store
                if (!db.objectStoreNames.contains(this.STORE_RESULTS)) {
                    const resultsStore = db.createObjectStore(this.STORE_RESULTS, {
                        keyPath: 'id',
                        autoIncrement: true
                    });

                    // 建立索引（用於查詢）
                    resultsStore.createIndex('timestamp', 'timestamp', { unique: false });
                    resultsStore.createIndex('templateName', 'templateName', { unique: false });
                    resultsStore.createIndex('score', 'score', { unique: false });

                    console.log('✅ Results object store 建立成功');
                }

                // 建立 templates object store
                if (!db.objectStoreNames.contains(this.STORE_TEMPLATES)) {
                    const templatesStore = db.createObjectStore(this.STORE_TEMPLATES, {
                        keyPath: 'name'
                    });

                    templatesStore.createIndex('createdAt', 'createdAt', { unique: false });

                    console.log('✅ Templates object store 建立成功');
                }
            };

            request.onsuccess = (event) => {
                this.db = event.target.result;
                this.isInitialized = true;

                console.log(`✅ IndexedDB 已初始化: ${this.DB_NAME} v${this.DB_VERSION}`);
                resolve();
            };

            request.onerror = (event) => {
                console.error('❌ IndexedDB 初始化失敗:', event.target.error);
                reject(new Error('IndexedDB 初始化失敗: ' + event.target.error));
            };

            request.onblocked = () => {
                console.warn('⚠️ IndexedDB 被封鎖，請關閉其他使用此資料庫的分頁');
                reject(new Error('IndexedDB 被封鎖'));
            };
        });
    }

    /**
     * 確保資料庫已初始化
     * @private
     */
    _ensureInitialized() {
        if (!this.isInitialized || !this.db) {
            throw new Error('資料庫尚未初始化，請先呼叫 init()');
        }
    }

    /**
     * 儲存 OMR 處理結果
     * @param {Object} result - 處理結果物件
     * @param {Blob} result.originalImageBlob - 原始影像 Blob
     * @param {Blob} result.processedImageBlob - 處理後影像 Blob
     * @param {Object} result.answers - 答案物件 { 題號: 答案 }
     * @param {Number} result.score - 分數
     * @param {String} result.templateName - 使用的模板名稱
     * @param {Object} result.metadata - 其他中繼資料
     * @returns {Promise<number>} 儲存的記錄 ID
     */
    async saveResult(result) {
        this._ensureInitialized();

        // 驗證必要欄位
        if (!result.originalImageBlob || !(result.originalImageBlob instanceof Blob)) {
            throw new Error('originalImageBlob 必須是 Blob 類型');
        }

        if (!result.processedImageBlob || !(result.processedImageBlob instanceof Blob)) {
            throw new Error('processedImageBlob 必須是 Blob 類型');
        }

        // 驗證 answers 和 metadata 必須是物件類型
        if (result.answers && typeof result.answers !== 'object') {
            throw new Error('answers 必須是物件類型');
        }

        if (result.metadata && typeof result.metadata !== 'object') {
            throw new Error('metadata 必須是物件類型');
        }

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_RESULTS], 'readwrite');
                const store = transaction.objectStore(this.STORE_RESULTS);

                // 準備儲存的資料
                const data = {
                    timestamp: new Date(),
                    originalImageBlob: result.originalImageBlob,
                    processedImageBlob: result.processedImageBlob,
                    answers: result.answers || {},
                    score: result.score || 0,
                    templateName: result.templateName || 'default',
                    metadata: result.metadata || {}
                };

                const request = store.add(data);

                request.onsuccess = () => {
                    const id = request.result;
                    console.log(`✅ 結果已儲存，ID: ${id}`);
                    resolve(id);
                };

                request.onerror = () => {
                    console.error('❌ 儲存結果失敗:', request.error);
                    reject(new Error('儲存結果失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 查詢所有結果
     * @returns {Promise<Array>} 所有結果的陣列（依時間倒序）
     */
    async getAllResults() {
        this._ensureInitialized();

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_RESULTS], 'readonly');
                const store = transaction.objectStore(this.STORE_RESULTS);
                const index = store.index('timestamp');

                // 使用時間索引，倒序查詢（最新的在前）
                const request = index.openCursor(null, 'prev');
                const results = [];

                request.onsuccess = (event) => {
                    const cursor = event.target.result;

                    if (cursor) {
                        results.push(cursor.value);
                        cursor.continue();
                    } else {
                        console.log(`✅ 查詢到 ${results.length} 筆結果`);
                        resolve(results);
                    }
                };

                request.onerror = () => {
                    console.error('❌ 查詢結果失敗:', request.error);
                    reject(new Error('查詢結果失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 根據 ID 查詢單筆結果
     * @param {number} id - 結果 ID
     * @returns {Promise<Object|undefined>} 結果物件，若不存在則返回 undefined
     */
    async getResultById(id) {
        this._ensureInitialized();

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_RESULTS], 'readonly');
                const store = transaction.objectStore(this.STORE_RESULTS);
                const request = store.get(id);

                request.onsuccess = () => {
                    const result = request.result;

                    if (result) {
                        console.log(`✅ 找到結果，ID: ${id}`);
                    } else {
                        console.log(`⚠️ 找不到結果，ID: ${id}`);
                    }

                    resolve(result);
                };

                request.onerror = () => {
                    console.error('❌ 查詢結果失敗:', request.error);
                    reject(new Error('查詢結果失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 刪除單筆結果
     * @param {number} id - 結果 ID
     * @returns {Promise<void>}
     */
    async deleteResult(id) {
        this._ensureInitialized();

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_RESULTS], 'readwrite');
                const store = transaction.objectStore(this.STORE_RESULTS);
                const request = store.delete(id);

                request.onsuccess = () => {
                    console.log(`✅ 結果已刪除，ID: ${id}`);
                    resolve();
                };

                request.onerror = () => {
                    console.error('❌ 刪除結果失敗:', request.error);
                    reject(new Error('刪除結果失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 刪除所有結果
     * @returns {Promise<void>}
     */
    async deleteAllResults() {
        this._ensureInitialized();

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_RESULTS], 'readwrite');
                const store = transaction.objectStore(this.STORE_RESULTS);
                const request = store.clear();

                request.onsuccess = () => {
                    console.log('✅ 所有結果已清空');
                    resolve();
                };

                request.onerror = () => {
                    console.error('❌ 清空結果失敗:', request.error);
                    reject(new Error('清空結果失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 儲存 OMR 模板
     * @param {Object} template - 模板物件
     * @param {String} template.name - 模板名稱（唯一識別）
     * @param {Object} template.config - 模板配置
     * @param {Date} [template.createdAt] - 建立時間（可選）
     * @returns {Promise<void>}
     */
    async saveTemplate(template) {
        this._ensureInitialized();

        if (!template.name) {
            throw new Error('模板必須有 name 屬性');
        }

        if (!template.config) {
            throw new Error('模板必須有 config 屬性');
        }

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_TEMPLATES], 'readwrite');
                const store = transaction.objectStore(this.STORE_TEMPLATES);

                const data = {
                    name: template.name,
                    config: template.config,
                    createdAt: template.createdAt || new Date()
                };

                const request = store.put(data);  // put 會覆蓋已存在的

                request.onsuccess = () => {
                    console.log(`✅ 模板已儲存: ${template.name}`);
                    resolve();
                };

                request.onerror = () => {
                    console.error('❌ 儲存模板失敗:', request.error);
                    reject(new Error('儲存模板失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 根據名稱查詢模板
     * @param {String} name - 模板名稱
     * @returns {Promise<Object|undefined>} 模板物件，若不存在則返回 undefined
     */
    async getTemplate(name) {
        this._ensureInitialized();

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_TEMPLATES], 'readonly');
                const store = transaction.objectStore(this.STORE_TEMPLATES);
                const request = store.get(name);

                request.onsuccess = () => {
                    const template = request.result;

                    if (template) {
                        console.log(`✅ 找到模板: ${name}`);
                    } else {
                        console.log(`⚠️ 找不到模板: ${name}`);
                    }

                    resolve(template);
                };

                request.onerror = () => {
                    console.error('❌ 查詢模板失敗:', request.error);
                    reject(new Error('查詢模板失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 查詢所有模板
     * @returns {Promise<Array>} 所有模板的陣列
     */
    async getAllTemplates() {
        this._ensureInitialized();

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_TEMPLATES], 'readonly');
                const store = transaction.objectStore(this.STORE_TEMPLATES);
                const request = store.getAll();

                request.onsuccess = () => {
                    const templates = request.result;
                    console.log(`✅ 查詢到 ${templates.length} 個模板`);
                    resolve(templates);
                };

                request.onerror = () => {
                    console.error('❌ 查詢模板失敗:', request.error);
                    reject(new Error('查詢模板失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 刪除模板
     * @param {String} name - 模板名稱
     * @returns {Promise<void>}
     */
    async deleteTemplate(name) {
        this._ensureInitialized();

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([this.STORE_TEMPLATES], 'readwrite');
                const store = transaction.objectStore(this.STORE_TEMPLATES);
                const request = store.delete(name);

                request.onsuccess = () => {
                    console.log(`✅ 模板已刪除: ${name}`);
                    resolve();
                };

                request.onerror = () => {
                    console.error('❌ 刪除模板失敗:', request.error);
                    reject(new Error('刪除模板失敗: ' + request.error));
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    /**
     * 取得資料庫使用量估計
     * @returns {Promise<Object>} { usage: number, quota: number }
     */
    async getStorageEstimate() {
        if (!navigator.storage || !navigator.storage.estimate) {
            throw new Error('瀏覽器不支援 Storage Estimate API');
        }

        try {
            const estimate = await navigator.storage.estimate();

            return {
                usage: estimate.usage,
                quota: estimate.quota,
                usageInMB: (estimate.usage / (1024 * 1024)).toFixed(2),
                quotaInMB: (estimate.quota / (1024 * 1024)).toFixed(2),
                percentage: ((estimate.usage / estimate.quota) * 100).toFixed(2)
            };
        } catch (error) {
            console.error('❌ 無法取得儲存空間資訊:', error);
            throw error;
        }
    }

    /**
     * 關閉資料庫連線
     */
    close() {
        if (this.db) {
            this.db.close();
            this.db = null;
            this.isInitialized = false;
            console.log('✅ 資料庫連線已關閉');
        }
    }
}

// 匯出供其他模組使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = OMRStorage;
}
