/**
 * Batch Processor
 * 處理多張 OMR 答案卡的批次辨識
 */

class BatchProcessor {
  constructor() {
    this.files = [];
    this.template = null;
    this.config = null;
    this.evaluation = null;
    this.marker = null;
    this.options = {
      autoAlign: false,
      layoutMode: false
    };
    this.worker = null;
    this.currentIndex = 0;
    this.results = [];
    this.logs = [];
    this.isProcessing = false;
  }

  /**
   * 設定 Worker
   */
  setWorker(worker) {
    this.worker = worker;
  }

  /**
   * 設定檔案
   */
  setFiles(files) {
    this.files = Array.from(files);
    this.currentIndex = 0;
    this.results = [];
    this.logs = [];
  }

  /**
   * 設定模板
   */
  async setTemplate(file) {
    try {
      const text = await file.text();
      this.template = JSON.parse(text);
      this.log('info', `載入模板: ${file.name}`);
      return this.template;
    } catch (error) {
      this.log('error', `模板載入失敗: ${error.message}`);
      throw error;
    }
  }

  /**
   * 設定 Config
   */
  async setConfig(file) {
    if (!file) {
      this.config = null;
      return null;
    }

    try {
      const text = await file.text();
      this.config = JSON.parse(text);
      this.log('info', `載入設定檔: ${file.name}`);
      return this.config;
    } catch (error) {
      this.log('error', `設定檔載入失敗: ${error.message}`);
      throw error;
    }
  }

  /**
   * 設定 Evaluation
   */
  async setEvaluation(file) {
    if (!file) {
      this.evaluation = null;
      return null;
    }

    try {
      const text = await file.text();
      this.evaluation = JSON.parse(text);
      this.log('info', `載入評分標準檔: ${file.name}`);
      return this.evaluation;
    } catch (error) {
      this.log('error', `評分標準檔載入失敗: ${error.message}`);
      throw error;
    }
  }

  /**
   * 設定 Marker
   */
  async setMarker(file) {
    if (!file) {
      this.marker = null;
      return null;
    }

    try {
      this.marker = file;
      this.log('info', `載入自訂標記圖檔: ${file.name}`);
      return this.marker;
    } catch (error) {
      this.log('error', `標記圖檔載入失敗: ${error.message}`);
      throw error;
    }
  }

  /**
   * Load marker image to worker (loads as Image, converts to ImageData, sends to worker)
   */
  async loadMarkerToWorker(markerFile) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        const markerDataURL = e.target.result;

        // Load image in main thread to convert to ImageData
        const img = new Image();
        img.onload = () => {
          // Convert to ImageData
          const canvas = new OffscreenCanvas(img.width, img.height);
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0);
          const imageData = ctx.getImageData(0, 0, img.width, img.height);

          // Extract CropOnMarkers options from template
          let markerOptions = {};
          if (this.template && this.template.preProcessors) {
            const cropOnMarkersConfig = this.template.preProcessors.find(
              p => p.name === 'CropOnMarkers'
            );
            if (cropOnMarkersConfig && cropOnMarkersConfig.options) {
              markerOptions = cropOnMarkersConfig.options;
            }
          }

          // Create a unique ID for tracking this request
          const messageId = `marker_${Date.now()}`;

          // Set up one-time message listener for the response
          const responseHandler = (event) => {
            const { type, id, payload, error } = event.data;

            if (id === messageId) {
              // Remove listener after receiving response
              this.worker.removeEventListener('message', responseHandler);

              if (type === 'result' && payload && payload.success) {
                this.log('success', `標記圖檔已載入到 Worker: ${payload.markerSize[0]}x${payload.markerSize[1]}`);
                resolve(payload);
              } else if (type === 'error') {
                this.log('error', `Worker 標記載入失敗: ${error}`);
                reject(new Error(error));
              }
            }
          };

          this.worker.addEventListener('message', responseHandler);

          // Send marker ImageData to worker
          this.worker.postMessage({
            type: 'load_marker',
            id: messageId,
            payload: {
              imageData: {
                data: Array.from(imageData.data),
                width: imageData.width,
                height: imageData.height
              },
              options: markerOptions
            }
          });
        };

        img.onerror = () => {
          reject(new Error('標記圖檔載入失敗'));
        };

        img.src = markerDataURL;
      };

      reader.onerror = () => {
        reject(new Error('標記圖檔讀取失敗'));
      };

      reader.readAsDataURL(markerFile);
    });
  }

  /**
   * 設定選項
   */
  setOptions(options) {
    this.options = { ...this.options, ...options };
  }

  /**
   * 開始批次處理
   */
  async startBatch(progressCallback, completionCallback) {
    if (this.isProcessing) {
      throw new Error('批次處理正在進行中');
    }

    if (this.files.length === 0) {
      throw new Error('沒有要處理的檔案');
    }

    if (!this.template) {
      throw new Error('未載入模板檔案');
    }

    this.isProcessing = true;
    this.currentIndex = 0;
    this.results = [];
    this.logs = [];

    this.log('info', `開始批次處理 ${this.files.length} 張圖片`);

    try {
      // Load marker image to worker if provided (once before batch processing)
      if (this.marker) {
        this.log('info', `載入標記圖檔到 Worker: ${this.marker.name}`);
        await this.loadMarkerToWorker(this.marker);
      }

      for (let i = 0; i < this.files.length; i++) {
        this.currentIndex = i;
        const file = this.files[i];

        this.log('info', `處理第 ${i + 1}/${this.files.length} 張: ${file.name}`);

        if (progressCallback) {
          progressCallback({
            current: i + 1,
            total: this.files.length,
            fileName: file.name,
            status: 'processing'
          });
        }

        try {
          const result = await this.processFile(file);
          this.results.push({
            file: file.name,
            status: 'success',
            result
          });

          this.log('success', `✓ ${file.name} 處理成功`);

          if (progressCallback) {
            progressCallback({
              current: i + 1,
              total: this.files.length,
              fileName: file.name,
              status: 'success'
            });
          }
        } catch (error) {
          this.results.push({
            file: file.name,
            status: 'error',
            error: error.message
          });

          this.log('error', `✗ ${file.name} 處理失敗: ${error.message}`);

          if (progressCallback) {
            progressCallback({
              current: i + 1,
              total: this.files.length,
              fileName: file.name,
              status: 'error',
              error: error.message
            });
          }
        }
      }

      this.log('success', `批次處理完成: ${this.results.filter(r => r.status === 'success').length}/${this.files.length} 成功`);

      if (completionCallback) {
        completionCallback(this.results);
      }
    } finally {
      this.isProcessing = false;
    }

    return this.results;
  }

  /**
   * 處理單個檔案
   */
  async processFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = async (e) => {
        try {
          const img = new Image();
          img.onload = async () => {
            try {
              // 準備處理參數
              const params = {
                image: img,
                template: this.template,
                config: this.config,
                evaluation: this.evaluation,
                marker: this.marker,
                options: this.options
              };

              // 使用 Worker 處理
              if (this.worker) {
                const result = await this.processWithWorker(img, params);
                resolve(result);
              } else {
                throw new Error('Worker 未初始化');
              }
            } catch (error) {
              reject(error);
            }
          };

          img.onerror = () => reject(new Error('圖片載入失敗'));
          img.src = e.target.result;
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error('檔案讀取失敗'));
      reader.readAsDataURL(file);
    });
  }

  /**
   * 使用 Worker 處理圖片
   */
  processWithWorker(img, params) {
    return new Promise((resolve, reject) => {
      // 將圖片轉換為 canvas
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

      // 發送到 Worker
      const messageId = Date.now();

      const handler = (e) => {
        if (e.data.type === 'omrComplete' && e.data.id === messageId) {
          this.worker.removeEventListener('message', handler);
          if (e.data.error) {
            reject(new Error(e.data.error));
          } else {
            resolve(e.data.result);
          }
        }
      };

      this.worker.addEventListener('message', handler);

      this.worker.postMessage({
        type: 'processOMR',
        id: messageId,
        imageData,
        template: params.template,
        config: params.config,
        evaluation: params.evaluation,
        options: params.options
      });

      // 設定超時
      setTimeout(() => {
        this.worker.removeEventListener('message', handler);
        reject(new Error('處理超時'));
      }, 30000); // 30 seconds timeout
    });
  }

  /**
   * 記錄日誌
   */
  log(level, message) {
    const timestamp = new Date().toLocaleTimeString('zh-TW');
    const logEntry = {
      timestamp,
      level,
      message
    };
    this.logs.push(logEntry);
  }

  /**
   * 取得日誌
   */
  getLogs() {
    return this.logs;
  }

  /**
   * 取得結果
   */
  getResults() {
    return this.results;
  }

  /**
   * 匯出 CSV（與GRADIO版本相容格式）
   */
  exportCSV() {
    if (this.results.length === 0) {
      throw new Error('沒有可匯出的結果');
    }

    const successResults = this.results.filter(r => r.status === 'success');
    if (successResults.length === 0) {
      throw new Error('沒有成功處理的結果');
    }

    // 收集所有question fields (sorted)
    const allFields = new Set();
    successResults.forEach(r => {
      if (r.result && r.result.answers) {
        Object.keys(r.result.answers).forEach(key => allFields.add(key));
      }
    });

    // Sort fields: qr_id first, then q1, q2, ..., q80
    const sortedFields = Array.from(allFields).sort((a, b) => {
      if (a === 'qr_id') return -1;
      if (b === 'qr_id') return 1;
      if (a.startsWith('q') && b.startsWith('q')) {
        return parseInt(a.substring(1)) - parseInt(b.substring(1));
      }
      return a.localeCompare(b);
    });

    // Header: file_id, input_path, output_path, score, qr_id, q1, q2, ...
    const headers = ['file_id', 'input_path', 'output_path', 'score', ...sortedFields];
    const csvContent = ['\uFEFF' + headers.join(',')]; // UTF-8 BOM

    // Data rows
    successResults.forEach(r => {
      const fileName = this.escapeCSV(r.file);
      const inputPath = this.escapeCSV(r.file);
      const outputPath = ''; // 不適用於瀏覽器版本
      const score = r.result.score || 0;

      let row = `"${fileName}","${inputPath}","${outputPath}",${score}`;

      // Add answers for each field
      sortedFields.forEach(field => {
        const answer = r.result.answers?.[field] || [];
        // Join multiple answers with comma (e.g., ["A","B"] => "A,B")
        const answerStr = Array.isArray(answer) ? answer.join(',') : answer;
        row += `,"${this.escapeCSV(answerStr)}"`;
      });

      csvContent.push(row);
    });

    return csvContent.join('\n');
  }

  /**
   * Escape special characters for CSV format
   */
  escapeCSV(str) {
    if (typeof str !== 'string') return str;
    // Escape double quotes by doubling them
    return str.replace(/"/g, '""');
  }

  /**
   * 匯出 JSON
   */
  exportJSON() {
    return JSON.stringify(this.results, null, 2);
  }

  /**
   * 停止處理
   */
  stop() {
    this.isProcessing = false;
    this.log('warning', '批次處理已停止');
  }
}

// 如果在瀏覽器環境
if (typeof window !== 'undefined') {
  window.BatchProcessor = BatchProcessor;
}
