/**
 * OMR Image Processing Web Worker
 * 在獨立執行緒中執行影像處理，避免阻塞主執行緒 UI
 */

// Worker 全域變數
let cv = null;
let isOpenCVReady = false;
let processingQueue = [];
let isProcessing = false;
let currentTemplate = null;

// 訊息類型常數
const MessageType = {
  // 從主執行緒接收
  INIT: 'init',
  LOAD_TEMPLATE: 'load_template',
  PROCESS_IMAGE: 'process_image',
  PROCESS_OMR: 'processOMR',  // 批次處理使用

  // 回傳給主執行緒
  READY: 'ready',
  PROGRESS: 'progress',
  RESULT: 'result',
  ERROR: 'error'
};

// ============================================================
// Template Parsing Utilities (Python OMRChecker Compatible)
// ============================================================

/**
 * Field types definitions (from Python constants.py)
 */
const FIELD_TYPES = {
  'QTYPE_INT': {
    bubbleValues: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'],
    direction: 'vertical'
  },
  'QTYPE_INT_FROM_1': {
    bubbleValues: ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    direction: 'vertical'
  },
  'QTYPE_MCQ4': {
    bubbleValues: ['A', 'B', 'C', 'D'],
    direction: 'horizontal'
  },
  'QTYPE_MCQ5': {
    bubbleValues: ['A', 'B', 'C', 'D', 'E'],
    direction: 'horizontal'
  }
};

/**
 * Parse field string like "q1..5" into ["q1", "q2", "q3", "q4", "q5"]
 */
function parseFieldString(fieldString) {
  if (fieldString.includes('..')) {
    // Format: "prefix1..5" -> ["prefix1", "prefix2", "prefix3", "prefix4", "prefix5"]
    const match = fieldString.match(/^([^\d]+)(\d+)\.\.(\d+)$/);
    if (!match) {
      throw new Error(`Invalid field string format: ${fieldString}`);
    }
    const [, prefix, startStr, endStr] = match;
    const start = parseInt(startStr);
    const end = parseInt(endStr);

    if (start >= end) {
      throw new Error(`Invalid range in field string: ${fieldString}, start must be less than end`);
    }

    const result = [];
    for (let i = start; i <= end; i++) {
      result.push(`${prefix}${i}`);
    }
    return result;
  } else {
    return [fieldString];
  }
}

/**
 * Parse field labels array, expanding ranges
 */
function parseFields(fieldLabels) {
  const parsed = [];
  for (const fieldString of fieldLabels) {
    parsed.push(...parseFieldString(fieldString));
  }
  return parsed;
}

/**
 * Convert Python fieldBlocks format to unified bubble list
 */
function parseFieldBlocks(template) {
  if (!template.fieldBlocks) {
    return null;
  }

  const bubbles = [];
  const pageDimensions = template.pageDimensions || [850, 1202];
  const globalBubbleDimensions = template.bubbleDimensions || [32, 32];

  for (const [blockName, fieldBlock] of Object.entries(template.fieldBlocks)) {
    // Skip QR Code blocks - they are handled separately in detectAndParseAnswers
    const isQRBlock = fieldBlock.fieldType === 'QTYPE_CUSTOM' ||
                     blockName === 'QR_Code' ||
                     blockName.includes('QR');

    if (isQRBlock) {
      console.log(`[Worker] Skipping QR block: ${blockName}`);
      continue;
    }

    // Pre-fill with field type defaults
    let blockConfig = { ...fieldBlock };
    if (fieldBlock.fieldType && FIELD_TYPES[fieldBlock.fieldType]) {
      blockConfig = {
        ...blockConfig,
        ...FIELD_TYPES[fieldBlock.fieldType]
      };
    }

    // Set defaults
    const {
      origin = [0, 0],
      bubbleDimensions = globalBubbleDimensions,
      bubbleValues = [],
      bubblesGap = 40,
      direction = 'vertical',
      fieldLabels = [],
      labelsGap = 60
    } = blockConfig;

    // Parse field labels
    const parsedLabels = parseFields(fieldLabels);

    // Generate bubble grid (similar to Python's generate_bubble_grid)
    let leadPoint = [origin[0], origin[1]];

    for (const fieldLabel of parsedLabels) {
      let bubblePoint = [...leadPoint];

      for (const bubbleValue of bubbleValues) {
        bubbles.push({
          x: Math.round(bubblePoint[0]),
          y: Math.round(bubblePoint[1]),
          fieldLabel: fieldLabel,
          fieldValue: bubbleValue,
          width: bubbleDimensions[0],
          height: bubbleDimensions[1]
        });

        // Increment for next bubble value in this field
        if (direction === 'vertical') {
          bubblePoint[1] += bubblesGap; // y-increment (0-9 below each other)
        } else {
          bubblePoint[0] += bubblesGap; // x-increment (A/B/C/D side by side)
        }
      }

      // Move lead point for next field label
      if (direction === 'vertical') {
        leadPoint[0] += labelsGap; // x-increment for next digit
      } else {
        leadPoint[1] += labelsGap; // y-increment for next question
      }
    }
  }

  return {
    bubbles,
    pageDimensions,
    answers: template.answerKey || template.answers || {}
  };
}

/**
 * Parse our original regions format
 */
function parseRegionsFormat(template) {
  if (!template.layout || !template.layout.regions) {
    return null;
  }

  const bubbles = [];
  const regions = template.layout.regions;

  for (const region of regions) {
    const { origin, questions, options } = region;
    const startQ = questions.start;
    const endQ = questions.end;
    const questionGap = questions.gap || 65;
    const optionGap = options.gap || 80;
    const optionValues = options.values || ['A', 'B', 'C', 'D'];

    let yPos = origin.y;
    for (let qNum = startQ; qNum <= endQ; qNum++) {
      let xPos = origin.x;
      for (const optValue of optionValues) {
        bubbles.push({
          x: Math.round(xPos),
          y: Math.round(yPos),
          fieldLabel: `${qNum}`,
          fieldValue: optValue,
          width: template.bubble?.diameter || 32,
          height: template.bubble?.diameter || 32
        });
        xPos += optionGap;
      }
      yPos += questionGap;
    }
  }

  return {
    bubbles,
    pageDimensions: [template.page?.width || 850, template.page?.height || 1202],
    answers: template.answerKey || template.answers || {}
  };
}

/**
 * Unified template parser - auto-detects format
 */
function parseTemplate(template) {
  // Try Python fieldBlocks format first
  const fieldBlocksResult = parseFieldBlocks(template);
  if (fieldBlocksResult) {
    console.log('[Worker] Detected Python fieldBlocks format');
    return fieldBlocksResult;
  }

  // Try our regions format
  const regionsResult = parseRegionsFormat(template);
  if (regionsResult) {
    console.log('[Worker] Detected regions format');
    return regionsResult;
  }

  throw new Error('Unknown template format - must have either fieldBlocks or layout.regions');
}

/**
 * 處理從主執行緒來的訊息
 */
self.onmessage = function (e) {
  const { type, payload, id } = e.data;

  switch (type) {
    case MessageType.INIT:
      initOpenCV(payload.opencvPath, id);
      break;

    case MessageType.LOAD_TEMPLATE:
      loadTemplate(payload.template, id);
      break;

    case MessageType.PROCESS_IMAGE:
      queueImageProcessing(payload, id);
      break;

    case MessageType.PROCESS_OMR:
      // 批次處理專用 - 直接從 e.data 取得參數
      processOMRBatch(e.data);
      break;

    default:
      sendError('Unknown message type: ' + type, id);
  }
};

/**
 * 初始化 OpenCV.js
 */
function initOpenCV(opencvPath, id) {
  console.log(opencvPath);
  let checker_handle, timeout_handle;
  checker_handle = null;
  timeout_handle = null;
  importScripts(opencvPath);
  checker_handle = setInterval(() => {
    // 設定 OpenCV.js 載入回調
    if (typeof self['cv'] === 'object') {
      cv = self['cv'];
      isOpenCVReady = true;
      console.log('[Worker] OpenCV.js 已就緒');
      sendMessage(MessageType.READY, {
        version: cv.getBuildInformation()
      });
      sendMessage(MessageType.RESULT, {
        version: cv.getBuildInformation()
      }, id);
      clearTimeout(timeout_handle);
      clearInterval(checker_handle);
    } else {
      console.log('OpenCV 仍在讀取中')
    }
  }, 500);

  timeout_handle = setTimeout(() => {
    console.log("openCV 初始化失敗")
    sendError('OpenCV.js 初始化失敗');
    clearInterval(checker_handle);
  }, 15000)
}

/**
 * 載入 OMR 模板
 */
function loadTemplate(template, id) {
  try {
    if (!isOpenCVReady) {
      throw new Error('OpenCV.js 尚未就緒');
    }

    currentTemplate = template;
    console.log('[Worker] 模板已載入:', template.name);

    sendMessage(MessageType.RESULT, {
      success: true,
      templateName: template.name
    }, id);

  } catch (error) {
    sendError('模板載入失敗: ' + error.message, id);
  }
}

/**
 * 將影像處理任務加入佇列
 */
function queueImageProcessing(payload, id) {
  processingQueue.push({ payload, id });

  // 如果沒有正在處理，開始處理佇列
  if (!isProcessing) {
    processNextInQueue();
  }
}

/**
 * 處理佇列中的下一個任務
 */
async function processNextInQueue() {
  if (processingQueue.length === 0) {
    isProcessing = false;
    return;
  }

  isProcessing = true;
  const { payload, id } = processingQueue.shift();

  try {
    await processImage(payload, id);
  } catch (error) {
    sendError('處理失敗: ' + error.message, id);
  }

  // 處理下一個任務
  processNextInQueue();
}

/**
 * 處理影像（主要處理流程）
 */
async function processImage(payload, id) {
  const processedMats = [];  // 追蹤建立的 Mat，確保記憶體釋放

  try {
    if (!isOpenCVReady) {
      throw new Error('OpenCV.js 尚未就緒');
    }

    const { imageData, width, height } = payload;

    // 回報進度: 0% - 開始處理
    sendProgress(0, '開始處理影像...', id);

    // 1. 建立 Mat 從 ImageData
    sendProgress(10, '載入影像...', id);
    const src = cv.matFromImageData({
      data: new Uint8ClampedArray(imageData),
      width: width,
      height: height
    });
    processedMats.push(src);

    // 2. 預處理（灰階、模糊、二值化）
    sendProgress(20, '執行預處理...', id);
    const preprocessResults = preprocessImage(src);
    processedMats.push(...Object.values(preprocessResults));

    // 3. 透視校正 - 使用模板的 pageDimensions (如果有)
    sendProgress(40, '執行透視校正...', id);
    const templatePageDimensions = currentTemplate ? currentTemplate.pageDimensions : null;
    const perspectiveResult = correctPerspective(src, templatePageDimensions);
    processedMats.push(perspectiveResult.corrected);
    if (perspectiveResult.visualization) {
      processedMats.push(perspectiveResult.visualization);
    }

    // 4. 答案檢測（如果有模板）
    let omrResult = null;
    if (currentTemplate && perspectiveResult.corrected) {
      sendProgress(60, '檢測答案標記...', id);
      omrResult = detectAndParseAnswers(
        perspectiveResult.corrected,
        currentTemplate
      );
      if (omrResult.visualization) {
        processedMats.push(omrResult.visualization);
      }
    }

    // 5. 準備回傳結果
    sendProgress(80, '準備結果...', id);
    const results = {
      // 將 Mat 轉換為 ImageData 以便傳回主執行緒
      original: matToImageData(src),
      grayscale: matToImageData(preprocessResults.grayscale),
      blurred: matToImageData(preprocessResults.blurred),
      binary: matToImageData(preprocessResults.binary),
      corners: perspectiveResult.visualization ?
        matToImageData(perspectiveResult.visualization) : null,
      corrected: matToImageData(perspectiveResult.corrected),
      omr: omrResult ? {
        ...omrResult,
        visualization: omrResult.visualization ?
          matToImageData(omrResult.visualization) : null
      } : null
    };

    // 6. 完成
    sendProgress(100, '處理完成！', id);
    sendMessage(MessageType.RESULT, results, id);

  } catch (error) {
    console.error('[Worker] 處理錯誤:', error);
    sendError('影像處理失敗: ' + error.message, id);

  } finally {
    // 確保釋放所有 Mat
    processedMats.forEach(mat => {
      if (mat && typeof mat.delete === 'function') {
        try {
          mat.delete();
        } catch (e) {
          console.warn('[Worker] Mat 釋放失敗:', e);
        }
      }
    });
  }
}

/**
 * 預處理影像（灰階、模糊、二值化）
 */
function preprocessImage(src) {
  // 1. 灰階轉換
  const grayscale = new cv.Mat();
  cv.cvtColor(src, grayscale, cv.COLOR_RGBA2GRAY);

  // 2. 高斯模糊降噪
  const blurred = new cv.Mat();
  const ksize = new cv.Size(5, 5);
  cv.GaussianBlur(grayscale, blurred, ksize, 0);

  // 3. 自適應二值化
  const binary = new cv.Mat();
  cv.adaptiveThreshold(
    blurred,
    binary,
    255,
    cv.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv.THRESH_BINARY,
    11,
    2
  );

  return {
    grayscale,
    blurred,
    binary
  };
}

/**
 * 透視校正
 */
function correctPerspective(src, templatePageDimensions = null) {
  const tempMats = [];

  try {
    // 1. 灰階轉換
    const gray = new cv.Mat();
    cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
    tempMats.push(gray);

    // 2. 高斯模糊
    const blurred = new cv.Mat();
    cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0);
    tempMats.push(blurred);

    // 3. Canny 邊緣檢測
    const edges = new cv.Mat();
    cv.Canny(blurred, edges, 50, 150);
    tempMats.push(edges);

    // 4. 形態學操作 (閉運算)
    const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(5, 5));
    tempMats.push(kernel);

    const dilated = new cv.Mat();
    cv.dilate(edges, dilated, kernel);
    tempMats.push(dilated);

    const closed = new cv.Mat();
    cv.morphologyEx(dilated, closed, cv.MORPH_CLOSE, kernel);
    tempMats.push(closed);

    // 5. 查找輪廓
    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    cv.findContours(
      closed,
      contours,
      hierarchy,
      cv.RETR_EXTERNAL,
      cv.CHAIN_APPROX_SIMPLE
    );
    tempMats.push(hierarchy);

    // 6. 找出最大的四邊形輪廓
    let maxArea = 0;
    let bestApprox = null;

    for (let i = 0; i < contours.size(); i++) {
      const contour = contours.get(i);
      const area = cv.contourArea(contour);

      // 計算輪廓周長
      const perimeter = cv.arcLength(contour, true);

      // 多邊形近似
      const approx = new cv.Mat();
      cv.approxPolyDP(contour, approx, 0.02 * perimeter, true);

      // 檢查是否為四邊形且面積夠大
      if (approx.rows === 4 && area > maxArea && area > src.rows * src.cols * 0.1) {
        maxArea = area;
        if (bestApprox) {
          bestApprox.delete();
        }
        bestApprox = approx;
      } else {
        approx.delete();
      }

      contour.delete();
    }
    contours.delete();

    if (!bestApprox) {
      throw new Error('找不到答案卡邊界');
    }

    // 7. 提取並排序角點
    const corners = sortCorners(bestApprox);
    bestApprox.delete();

    // 8. 計算目標尺寸
    const [tl, tr, br, bl] = corners;

    // 如果有提供模板的 pageDimensions，使用它；否則根據檢測到的角點計算
    let outputWidth, outputHeight;
    if (templatePageDimensions && Array.isArray(templatePageDimensions) && templatePageDimensions.length === 2) {
      outputWidth = templatePageDimensions[0];
      outputHeight = templatePageDimensions[1];
      console.log(`[Worker] Using template pageDimensions: ${outputWidth}x${outputHeight}`);
    } else {
      const widthTop = Math.hypot(tr.x - tl.x, tr.y - tl.y);
      const widthBottom = Math.hypot(br.x - bl.x, br.y - bl.y);
      outputWidth = Math.max(widthTop, widthBottom);

      const heightLeft = Math.hypot(bl.x - tl.x, bl.y - tl.y);
      const heightRight = Math.hypot(br.x - tr.x, br.y - tr.y);
      outputHeight = Math.max(heightLeft, heightRight);
      console.log(`[Worker] Calculated dimensions from corners: ${outputWidth}x${outputHeight}`);
    }

    // 9. 建立透視變換矩陣
    const srcPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
      tl.x, tl.y,
      tr.x, tr.y,
      br.x, br.y,
      bl.x, bl.y
    ]);
    tempMats.push(srcPoints);

    const dstPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
      0, 0,
      outputWidth, 0,
      outputWidth, outputHeight,
      0, outputHeight
    ]);
    tempMats.push(dstPoints);

    const M = cv.getPerspectiveTransform(srcPoints, dstPoints);
    tempMats.push(M);

    // 10. 應用透視變換
    const corrected = new cv.Mat();
    cv.warpPerspective(
      src,
      corrected,
      M,
      new cv.Size(outputWidth, outputHeight),
      cv.INTER_LINEAR,
      cv.BORDER_CONSTANT,
      new cv.Scalar(255, 255, 255, 255)  // White border
    );

    // 11. 建立視覺化影像（顯示檢測到的角點）
    const visualization = src.clone();
    corners.forEach((corner, idx) => {
      cv.circle(
        visualization,
        new cv.Point(corner.x, corner.y),
        10,
        [0, 255, 0, 255],
        -1
      );

      cv.putText(
        visualization,
        String(idx + 1),
        new cv.Point(corner.x + 15, corner.y + 15),
        cv.FONT_HERSHEY_SIMPLEX,
        1,
        [255, 0, 0, 255],
        2
      );
    });

    return {
      corrected,
      visualization,
      corners
    };

  } finally {
    // 釋放臨時 Mat
    tempMats.forEach(mat => {
      if (mat && typeof mat.delete === 'function') {
        try {
          mat.delete();
        } catch (e) {
          console.warn('[Worker] 臨時 Mat 釋放失敗:', e);
        }
      }
    });
  }
}

/**
 * 排序四個角點（左上、右上、右下、左下）
 */
function sortCorners(approx) {
  // 將 Mat 轉換為座標陣列
  // Note: cv.approxPolyDP returns CV_32SC2 (32-bit signed integer, 2 channels)
  const points = [];
  for (let i = 0; i < approx.rows; i++) {
    points.push({
      x: approx.data32S[i * 2],
      y: approx.data32S[i * 2 + 1]
    });
  }

  // 計算質心
  const centerX = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const centerY = points.reduce((sum, p) => sum + p.y, 0) / points.length;

  // 分類角點
  let tl = null, tr = null, br = null, bl = null;

  points.forEach(p => {
    if (p.x < centerX && p.y < centerY) tl = p;
    else if (p.x >= centerX && p.y < centerY) tr = p;
    else if (p.x >= centerX && p.y >= centerY) br = p;
    else bl = p;
  });

  return [tl, tr, br, bl];
}

/**
 * 檢測 QR Code
 */
function detectQRCode(img, fieldBlock) {
  try {
    // 取得 QR Code 區域
    const origin = fieldBlock.origin || [0, 0];
    const bubbleDims = fieldBlock.bubbleDimensions || [50, 50];
    const shift = fieldBlock.shift || 0;

    const x = origin[0] + shift;
    const y = origin[1];
    const boxW = bubbleDims[0];
    const boxH = bubbleDims[1];

    console.log(`[Worker] QR Code detection: img size=${img.cols}x${img.rows}, origin=[${origin[0]}, ${origin[1]}], shift=${shift}, bubbleDims=[${boxW}, ${boxH}]`);

    // QR Code 區域需要較大的範圍
    const qrSize = Math.max(boxW, boxH) * 50;
    const x1 = Math.max(0, x - Math.floor(qrSize / 2));
    const y1 = Math.max(0, y - Math.floor(qrSize / 2));
    const x2 = Math.min(img.cols, x + Math.floor(qrSize / 2));
    const y2 = Math.min(img.rows, y + Math.floor(qrSize / 2));

    console.log(`[Worker] QR region: qrSize=${qrSize}, rect=[${x1}, ${y1}, ${x2-x1}, ${y2-y1}]`);

    // 提取 QR Code 區域
    const rect = new cv.Rect(x1, y1, x2 - x1, y2 - y1);
    const qrRegion = img.roi(rect);

    // 轉換為灰階
    let qrGray;
    if (qrRegion.channels() === 4) {
      qrGray = new cv.Mat();
      cv.cvtColor(qrRegion, qrGray, cv.COLOR_RGBA2GRAY);
    } else if (qrRegion.channels() === 3) {
      qrGray = new cv.Mat();
      cv.cvtColor(qrRegion, qrGray, cv.COLOR_RGB2GRAY);
    } else {
      qrGray = qrRegion.clone();
    }

    // 使用 OpenCV.js 的 QRCodeDetector
    const qrDetector = new cv.QRCodeDetector();
    const decodedInfo = qrDetector.detectAndDecode(qrGray);

    // 清理
    qrRegion.delete();
    if (qrGray !== qrRegion) {
      qrGray.delete();
    }

    // 檢查解碼結果
    if (decodedInfo && decodedInfo.length > 0) {
      console.log(`[Worker] QR Code decoded successfully: ${decodedInfo}`);
      return {
        data: decodedInfo.trim(),
        success: true
      };
    } else {
      console.warn('[Worker] QR Code detection returned empty string');
      return null;
    }
  } catch (error) {
    console.error('[Worker] QR Code detection error:', error);
    return null;
  }
}

/**
 * 檢測並解析答案（使用unified template format）
 */
function detectAndParseAnswers(correctedMat, template) {
  const tempMats = [];

  try {
    // Parse template to get expected bubble positions
    const parsedTemplate = parseTemplate(template);
    const { bubbles: expectedBubbles, answers: answerKey } = parsedTemplate;

    console.log(`[Worker] Expected ${expectedBubbles.length} bubbles from template`);

    // 初始化答案物件
    const answers = {};

    // 1. 檢測 QR Code（如果模板中有定義）
    if (template.fieldBlocks) {
      for (const [blockName, fieldBlock] of Object.entries(template.fieldBlocks)) {
        // 檢查是否為 QR Code 欄位
        const isQRBlock = fieldBlock.fieldType === 'QTYPE_CUSTOM' ||
                         blockName === 'QR_Code' ||
                         (fieldBlock.bubbleValues && fieldBlock.bubbleValues.length === 1 && blockName.includes('QR'));

        if (isQRBlock) {
          try {
            const qrResult = detectQRCode(correctedMat, fieldBlock);
            if (qrResult && qrResult.data) {
              const fieldLabel = fieldBlock.fieldLabels ? fieldBlock.fieldLabels[0] : 'qr_id';
              answers[fieldLabel] = qrResult.data;
              console.log(`[Worker] QR Code decoded: ${qrResult.data}`);
            } else {
              const fieldLabel = fieldBlock.fieldLabels ? fieldBlock.fieldLabels[0] : 'qr_id';
              answers[fieldLabel] = fieldBlock.emptyVal || '';
              console.warn('[Worker] QR Code detection failed');
            }
          } catch (error) {
            console.error('[Worker] QR Code detection error:', error);
          }
        }
      }
    }

    // 2. 轉換為灰階（用於氣泡檢測）
    const gray = new cv.Mat();
    cv.cvtColor(correctedMat, gray, cv.COLOR_RGBA2GRAY);
    tempMats.push(gray);

    // 3. 二值化
    const binary = new cv.Mat();
    cv.threshold(gray, binary, 0, 255, cv.THRESH_BINARY_INV | cv.THRESH_OTSU);
    tempMats.push(binary);

    // 4. Initialize all question fields with empty arrays
    // This ensures every question appears in results, even if no bubbles are marked
    const allFieldLabels = new Set();
    for (const expectedBubble of expectedBubbles) {
      allFieldLabels.add(expectedBubble.fieldLabel);
    }
    allFieldLabels.forEach(label => {
      if (!answers[label]) {
        answers[label] = [];
      }
    });

    // 5. Analyze each expected bubble's fill ratio
    const fillThreshold = template.detection?.fillThreshold ||
                          template.bubble?.fillThreshold || 0.4;

    const visualizationData = [];

    for (const expectedBubble of expectedBubbles) {
      const { x, y, width, height, fieldLabel, fieldValue } = expectedBubble;

      // Create ROI rect for this bubble
      // Note: x, y are top-left corner coordinates (not center), same as Python version
      const roi = new cv.Rect(
        Math.max(0, x),
        Math.max(0, y),
        width,
        height
      );

      // Ensure ROI is within image bounds
      if (roi.x + roi.width > binary.cols) {
        roi.width = binary.cols - roi.x;
      }
      if (roi.y + roi.height > binary.rows) {
        roi.height = binary.rows - roi.y;
      }

      if (roi.width <= 0 || roi.height <= 0) {
        console.warn(`[Worker] Invalid ROI for bubble ${fieldLabel}=${fieldValue}:`, roi);
        continue;
      }

      // Extract ROI
      const binaryRoi = binary.roi(roi);
      const filledPixels = cv.countNonZero(binaryRoi);
      binaryRoi.delete();

      const totalPixels = roi.width * roi.height;
      const fillRatio = filledPixels / totalPixels;

      // Check if filled
      const isFilled = fillRatio > fillThreshold;

      if (isFilled) {
        answers[fieldLabel].push(fieldValue);
      }

      // Store for visualization
      visualizationData.push({
        x, y, width, height,
        fieldLabel, fieldValue,
        isFilled,
        fillRatio
      });
    }

    // 建立視覺化結果 - 只標記填塗的格子，不顯示對錯
    const visualization = correctedMat.clone();

    for (const data of visualizationData) {
      const { x, y, width, height, fieldLabel, fieldValue, isFilled, fillRatio } = data;

      const studentAnswers = answers[fieldLabel] || [];
      const isSelected = studentAnswers.includes(fieldValue);

      // 選擇顏色：只區分填塗/未填塗，不顯示對錯
      let color;
      if (isSelected) {
        color = [0, 255, 0, 255];  // 綠色 - 已填塗
      } else {
        color = [200, 200, 200, 255];  // 淺灰色 - 未填塗
      }

      // Draw circle at bubble position
      cv.circle(
        visualization,
        new cv.Point(x, y),
        Math.floor(Math.max(width, height) / 2),
        color,
        2
      );

      // 如果已填塗，標記填塗比例
      if (isSelected) {
        cv.putText(
          visualization,
          `${Math.round(fillRatio * 100)}%`,
          new cv.Point(x + 15, y + 5),
          cv.FONT_HERSHEY_SIMPLEX,
          0.3,
          [0, 255, 0, 255],
          1
        );
      }
    }

    return {
      answers,
      visualization
    };

  } finally {
    tempMats.forEach(mat => {
      if (mat && typeof mat.delete === 'function') {
        try {
          mat.delete();
        } catch (e) {
          console.warn('[Worker] 臨時 Mat 釋放失敗:', e);
        }
      }
    });
  }
}

/**
 * 計算分數
 */
function calculateScore(studentAnswers, correctAnswers) {
  const totalQuestions = Object.keys(correctAnswers).length;
  let correctCount = 0;
  let incorrectCount = 0;
  let unansweredCount = 0;

  const details = {};

  for (const questionNo in correctAnswers) {
    const correct = correctAnswers[questionNo];
    const student = studentAnswers[questionNo] || [];

    const isCorrect = JSON.stringify(correct.sort()) === JSON.stringify(student.sort());

    if (student.length === 0) {
      unansweredCount++;
      details[questionNo] = {
        correct,
        student: null,
        status: 'unanswered',
        isCorrect: false
      };
    } else if (isCorrect) {
      correctCount++;
      details[questionNo] = {
        correct,
        student,
        status: 'correct',
        isCorrect: true
      };
    } else {
      incorrectCount++;
      details[questionNo] = {
        correct,
        student,
        status: 'incorrect',
        isCorrect: false
      };
    }
  }

  const score = correctCount;
  const totalPoints = totalQuestions;
  const percentage = ((score / totalPoints) * 100).toFixed(2);

  return {
    score,
    totalPoints,
    percentage,
    correctCount,
    incorrectCount,
    unansweredCount,
    totalQuestions,
    details
  };
}

/**
 * 將 Mat 轉換為 ImageData
 */
function matToImageData(mat) {
  // 確保 Mat 是 RGBA 格式
  let rgba = mat;
  if (mat.channels() === 1) {
    rgba = new cv.Mat();
    cv.cvtColor(mat, rgba, cv.COLOR_GRAY2RGBA);
  } else if (mat.channels() === 3) {
    rgba = new cv.Mat();
    cv.cvtColor(mat, rgba, cv.COLOR_RGB2RGBA);
  }

  const imageData = {
    data: Array.from(rgba.data),
    width: rgba.cols,
    height: rgba.rows
  };

  // 如果轉換了，釋放臨時 Mat
  if (rgba !== mat) {
    rgba.delete();
  }

  return imageData;
}

/**
 * 發送訊息給主執行緒
 */
function sendMessage(type, payload, id = null) {
  self.postMessage({
    type,
    payload,
    id
  });
}

/**
 * 發送進度更新
 */
function sendProgress(percent, message, id) {
  sendMessage(MessageType.PROGRESS, {
    percent,
    message
  }, id);
}

/**
 * 發送錯誤
 */
function sendError(message, id = null) {
  sendMessage(MessageType.ERROR, {
    message
  }, id);
}

/**
 * 批次處理 OMR（給 BatchProcessor 使用）
 */
async function processOMRBatch(data) {
  const { id, imageData, template, config, evaluation, options } = data;
  const processedMats = [];

  try {
    if (!isOpenCVReady) {
      throw new Error('OpenCV.js 尚未就緒');
    }

    // 如果提供了模板，設定為當前模板
    if (template) {
      currentTemplate = template;
    }

    // 1. 建立 Mat 從 ImageData
    const src = cv.matFromImageData({
      data: new Uint8ClampedArray(imageData.data),
      width: imageData.width,
      height: imageData.height
    });
    processedMats.push(src);

    // 2. 預處理
    const preprocessResults = preprocessImage(src);
    processedMats.push(...Object.values(preprocessResults));

    // 3. 透視校正 - 使用模板的 pageDimensions (如果有)
    const templatePageDimensions = currentTemplate ? currentTemplate.pageDimensions : null;
    const perspectiveResult = correctPerspective(src, templatePageDimensions);
    processedMats.push(perspectiveResult.corrected);
    if (perspectiveResult.visualization) {
      processedMats.push(perspectiveResult.visualization);
    }

    // 4. 答案檢測
    let omrResult = null;
    if (currentTemplate && perspectiveResult.corrected) {
      omrResult = detectAndParseAnswers(
        perspectiveResult.corrected,
        currentTemplate
      );
      if (omrResult.visualization) {
        processedMats.push(omrResult.visualization);
      }
    }

    // 5. 轉換標記後的圖片為 ImageData
    let markedImageData = null;
    if (omrResult && omrResult.visualization) {
      markedImageData = matToImageData(omrResult.visualization);
    }

    // 6. 準備結果 - 只回傳辨識到的答案，不評分
    const result = {
      answers: omrResult ? omrResult.answers : {},
      markedImage: markedImageData,
      // 統計資訊
      totalQuestions: omrResult ? Object.keys(omrResult.answers).length : 0,
      answeredQuestions: omrResult ?
        Object.values(omrResult.answers).filter(a => a && a.length > 0).length : 0
    };

    // 8. 發送完成訊息
    self.postMessage({
      type: 'omrComplete',
      id: id,
      result: result
    });

  } catch (error) {
    console.error('[Worker] 批次處理錯誤:', error);
    self.postMessage({
      type: 'omrComplete',
      id: id,
      error: error.message
    });

  } finally {
    // 釋放所有 Mat
    processedMats.forEach(mat => {
      if (mat && typeof mat.delete === 'function') {
        try {
          mat.delete();
        } catch (e) {
          console.warn('[Worker] Mat 釋放失敗:', e);
        }
      }
    });
  }
}

console.log('[Worker] Image Worker 已載入');
