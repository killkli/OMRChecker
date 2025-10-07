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
let markerImage = null;  // Preprocessed marker for CropOnMarkers

// 訊息類型常數
const MessageType = {
  // 從主執行緒接收
  INIT: 'init',
  LOAD_TEMPLATE: 'load_template',
  LOAD_MARKER: 'load_marker',
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
    return fieldBlocksResult;
  }

  // Try our regions format
  const regionsResult = parseRegionsFormat(template);
  if (regionsResult) {
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

    case MessageType.LOAD_MARKER:
      loadMarker(payload.imageData, payload.options, id);
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
  let checker_handle, timeout_handle;
  checker_handle = null;
  timeout_handle = null;
  importScripts(opencvPath);
  checker_handle = setInterval(() => {
    // 設定 OpenCV.js 載入回調
    if (typeof self['cv'] === 'object') {
      cv = self['cv'];
      isOpenCVReady = true;
      sendMessage(MessageType.READY, {
        version: cv.getBuildInformation()
      });
      sendMessage(MessageType.RESULT, {
        version: cv.getBuildInformation()
      }, id);
      clearTimeout(timeout_handle);
      clearInterval(checker_handle);
    }
  }, 500);

  timeout_handle = setTimeout(() => {
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

    sendMessage(MessageType.RESULT, {
      success: true,
      templateName: template.name
    }, id);

  } catch (error) {
    sendError('模板載入失敗: ' + error.message, id);
  }
}

/**
 * 載入並預處理 Marker 影像 (Python CropOnMarkers 相容)
 * @param {object} imageData - ImageData from main thread
 * @param {object} options - CropOnMarkers 選項
 */
function loadMarker(imageData, options, id) {
  let marker = null;
  let resized = null;
  let blurred = null;
  let normalized = null;

  try {
    if (!isOpenCVReady) {
      throw new Error('OpenCV.js 尚未就緒');
    }

    // 1. Convert ImageData to cv.Mat
    marker = cv.matFromImageData({
      data: new Uint8ClampedArray(imageData.data),
      width: imageData.width,
      height: imageData.height
    });

    // 2. Convert to grayscale if needed
    if (marker.channels() > 1) {
      const gray = new cv.Mat();
      cv.cvtColor(marker, gray, cv.COLOR_RGBA2GRAY);
      marker.delete();
      marker = gray;
    }

    // 3. Resize based on sheetToMarkerWidthRatio (matching Python logic)
    // Python: marker = resize_util(marker, processing_width / sheetToMarkerWidthRatio)
    const ratio = options.sheetToMarkerWidthRatio || 10;
    const pageDimensions = currentTemplate?.pageDimensions || [1850, 2720];
    const processingWidth = pageDimensions[0];
    const targetWidth = Math.round(processingWidth / ratio);
    // Maintain aspect ratio
    const aspectRatio = marker.rows / marker.cols;
    const targetHeight = Math.round(targetWidth * aspectRatio);
    resized = new cv.Mat();
    cv.resize(marker, resized, new cv.Size(targetWidth, targetHeight), 0, 0, cv.INTER_AREA);
    marker.delete();  // Don't need original anymore
    marker = null;

    // 4. Apply Gaussian blur
    blurred = new cv.Mat();
    cv.GaussianBlur(resized, blurred, new cv.Size(5, 5), 0);
    resized.delete();  // Don't need resized anymore
    resized = null;

    // 5. Normalize
    normalized = new cv.Mat();
    cv.normalize(blurred, normalized, 0, 255, cv.NORM_MINMAX);
    blurred.delete();  // Don't need blurred anymore
    blurred = null;

    // 6. Apply erode-subtract if enabled (default true)
    let processed = normalized.clone();
    if (options.apply_erode_subtract !== false) {
      const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(5, 5));
      const eroded = new cv.Mat();
      cv.erode(normalized, eroded, kernel, new cv.Point(-1, -1), 5);
      cv.subtract(normalized, eroded, processed);
      eroded.delete();
      kernel.delete();
    }
    normalized.delete();  // Don't need normalized anymore
    normalized = null;

    // Store the processed marker globally
    if (markerImage) {
      markerImage.delete();
    }
    markerImage = processed;

    sendMessage(MessageType.RESULT, {
      success: true,
      markerSize: [markerImage.cols, markerImage.rows]
    }, id);

  } catch (error) {
    // Cleanup on error
    if (marker) marker.delete();
    if (resized) resized.delete();
    if (blurred) blurred.delete();
    if (normalized) normalized.delete();
    sendError('Marker 載入失敗: ' + error.message, id);
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

    // 3. 透視校正 - 使用模板的 pageDimensions 和 CropOnMarkers 設定
    sendProgress(40, '執行透視校正...', id);
    const templatePageDimensions = currentTemplate ? currentTemplate.pageDimensions : null;

    // Extract CropOnMarkers options from template
    let markerOptions = {};
    if (currentTemplate && currentTemplate.preProcessors) {
      const cropOnMarkersConfig = currentTemplate.preProcessors.find(
        p => p.name === 'CropOnMarkers'
      );
      if (cropOnMarkersConfig && cropOnMarkersConfig.options) {
        markerOptions = cropOnMarkersConfig.options;
      }
    }

    const perspectiveResult = correctPerspectiveWithMarkers(src, templatePageDimensions, markerOptions);
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
    } else {
      const widthTop = Math.hypot(tr.x - tl.x, tr.y - tl.y);
      const widthBottom = Math.hypot(br.x - bl.x, br.y - bl.y);
      outputWidth = Math.max(widthTop, widthBottom);

      const heightLeft = Math.hypot(bl.x - tl.x, bl.y - tl.y);
      const heightRight = Math.hypot(br.x - tr.x, br.y - tr.y);
      outputHeight = Math.max(heightLeft, heightRight);
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
 * 透視校正 - 使用 Marker 模板匹配 (Python CropOnMarkers 相容)
 * 完全複製 Python 版本的邏輯
 */
function correctPerspectiveWithMarkers(src, templatePageDimensions = null, markerOptions = {}) {
  const tempMats = [];
  // Assumes 'markerImage' is a globally accessible cv.Mat or similar.
  // We use a local variable to potentially hold a generated marker.
  let currentMarkerImage = markerImage;

  try {
    if (!currentMarkerImage) {
      console.warn('[Worker] No marker image provided. Attempting to generate default marker.');
      const defaultMarkerSize = markerOptions.default_marker_size || 100; // Use a default size of 100 pixels

      try {
        currentMarkerImage = generateDefaultMarkerImage(defaultMarkerSize, markerOptions);
        tempMats.push(currentMarkerImage); // Add to tempMats for proper memory release
        markerImage = currentMarkerImage;
      } catch (e) {
        console.error('[Worker] Failed to generate default marker image:', e);
        console.warn('[Worker] Falling back to contour detection as no marker image is available.');
        return correctPerspective(src, templatePageDimensions); // Fallback if generation fails
      }
    }

    // After attempting to load or generate, if 'currentMarkerImage' is still null/undefined,
    // then we genuinely don't have a marker to work with.
    if (!currentMarkerImage) {
      console.warn('[Worker] Marker image is still not available after generation attempt. Falling back to contour detection.');
      return correctPerspective(src, templatePageDimensions);
    }

    // 1. Convert to grayscale and prepare for template matching
    let gray = new cv.Mat();
    if (src.channels() > 1) {
      cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
    } else {
      gray = src.clone();
    }
    tempMats.push(gray);

    // 2. Apply erode-subtract to the image (matching Python preprocessing)
    const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(5, 5));
    tempMats.push(kernel);

    const eroded = new cv.Mat();
    cv.erode(gray, eroded, kernel, new cv.Point(-1, -1), 5);
    tempMats.push(eroded);

    const imageErodedSub = new cv.Mat();
    cv.subtract(gray, eroded, imageErodedSub);
    tempMats.push(imageErodedSub);

    // 3. Divide image into 4 quadrants (Python: midh = h//3, midw = w//2)
    const midW = Math.floor(src.cols / 2);
    const midH = Math.floor(src.rows / 3);  // HEIGHT divided by 3 (matching Python)
    const quadrants = [
      { origin: [0, 0], width: midW, height: midH },           // Top-left
      { origin: [midW, 0], width: src.cols - midW, height: midH },  // Top-right
      { origin: [0, midH], width: midW, height: src.rows - midH },  // Bottom-left
      { origin: [midW, midH], width: src.cols - midW, height: src.rows - midH }  // Bottom-right
    ];

    const centres = [];
    const maxMatchingValues = [];

    // 4. Multi-scale template matching in each quadrant
    // Python defaults: marker_rescale_range=[60, 130], marker_rescale_steps=15
    const rescaleRange = markerOptions.marker_rescale_range || [60, 130];
    const rescaleSteps = markerOptions.marker_rescale_steps || 15;
    const descentPerStep = (rescaleRange[1] - rescaleRange[0]) / rescaleSteps;
    const minMatchingThreshold = markerOptions.min_matching_threshold || 0.2;

    for (let q = 0; q < 4; q++) {
      const quad = quadrants[q];
      const rect = new cv.Rect(quad.origin[0], quad.origin[1], quad.width, quad.height);
      const roi = imageErodedSub.roi(rect);
      tempMats.push(roi);

      let maxT = -1;
      let bestMatchLoc = null;
      let bestScale = 1.0;

      // Multi-scale search from large to small
      for (let r0 = rescaleRange[1]; r0 >= rescaleRange[0]; r0 -= descentPerStep) {
        const s = r0 / 100.0;

        // Resize marker
        const rescaledMarker = new cv.Mat();
        const newSize = new cv.Size(
          Math.round(currentMarkerImage.cols * s), // Use currentMarkerImage
          Math.round(currentMarkerImage.rows * s)  // Use currentMarkerImage
        );
        cv.resize(currentMarkerImage, rescaledMarker, newSize, 0, 0, cv.INTER_AREA); // Use currentMarkerImage

        // Skip if marker is larger than ROI
        if (rescaledMarker.cols > roi.cols || rescaledMarker.rows > roi.rows) {
          rescaledMarker.delete();
          continue;
        }

        // Template matching
        const result = new cv.Mat();
        cv.matchTemplate(roi, rescaledMarker, result, cv.TM_CCOEFF_NORMED);

        const minMax = cv.minMaxLoc(result);
        const currentMaxT = minMax.maxVal;

        if (currentMaxT > maxT) {
          maxT = currentMaxT;
          bestMatchLoc = minMax.maxLoc;
          bestScale = s;
        }

        result.delete();
        rescaledMarker.delete();
      }

      // Validate match
      if (maxT < minMatchingThreshold) {
        throw new Error(`Marker not found in quadrant ${q + 1}, max matching: ${maxT.toFixed(3)}`);
      }

      // Calculate marker center in original image coordinates
      const markerWidth = currentMarkerImage.cols * bestScale; // Use currentMarkerImage
      const markerHeight = currentMarkerImage.rows * bestScale; // Use currentMarkerImage
      const centerX = quad.origin[0] + bestMatchLoc.x + markerWidth / 2;
      const centerY = quad.origin[1] + bestMatchLoc.y + markerHeight / 2;

      centres.push({ x: centerX, y: centerY });
      maxMatchingValues.push(maxT);
    }

    // 5. Validate matching variation
    const maxMatchingVariation = markerOptions.max_matching_variation || 0.41;
    const matchingDiff = Math.max(...maxMatchingValues) - Math.min(...maxMatchingValues);
    if (matchingDiff > maxMatchingVariation) {
      console.warn(`[Worker] High matching variation: ${matchingDiff.toFixed(3)} > ${maxMatchingVariation}`);
    }

    // 6. Order points (TL, TR, BR, BL)
    const orderedCentres = orderPoints(centres);

    // 7. Calculate output dimensions
    let outputWidth, outputHeight;
    if (templatePageDimensions && Array.isArray(templatePageDimensions) && templatePageDimensions.length === 2) {
      outputWidth = templatePageDimensions[0];
      outputHeight = templatePageDimensions[1];
    } else {
      const [tl, tr, br, bl] = orderedCentres;
      const widthTop = Math.hypot(tr.x - tl.x, tr.y - tl.y);
      const widthBottom = Math.hypot(br.x - bl.x, bl.y - bl.y);
      outputWidth = Math.max(widthTop, widthBottom);

      const heightLeft = Math.hypot(bl.x - tl.x, bl.y - tl.y);
      const heightRight = Math.hypot(br.x - tr.x, br.y - tr.y);
      outputHeight = Math.max(heightLeft, heightRight);
    }

    // 8. Compute perspective transform
    const srcPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
      orderedCentres[0].x, orderedCentres[0].y,
      orderedCentres[1].x, orderedCentres[1].y,
      orderedCentres[2].x, orderedCentres[2].y,
      orderedCentres[3].x, orderedCentres[3].y
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

    // 9. Apply perspective transform
    const corrected = new cv.Mat();
    cv.warpPerspective(
      src,
      corrected,
      M,
      new cv.Size(outputWidth, outputHeight),
      cv.INTER_LINEAR,
      cv.BORDER_CONSTANT,
      new cv.Scalar(255, 255, 255, 255)
    );

    // 10. Create visualization
    const visualization = src.clone();
    orderedCentres.forEach((center, idx) => {
      cv.circle(
        visualization,
        new cv.Point(center.x, center.y),
        10,
        [0, 255, 0, 255],
        -1
      );

      cv.putText(
        visualization,
        String(idx + 1),
        new cv.Point(center.x + 15, center.y + 15),
        cv.FONT_HERSHEY_SIMPLEX,
        1,
        [255, 0, 0, 255],
        2
      );
    });

    return {
      corrected,
      visualization,
      corners: orderedCentres
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

function correctPerspectiveWithMarkers(src, templatePageDimensions = null, markerOptions = {}) {
  const tempMats = [];

  try {
    if (!markerImage) {
      console.warn('[Worker] Marker not loaded, falling back to contour detection');
      return correctPerspective(src, templatePageDimensions);
    }

    // 1. Convert to grayscale and prepare for template matching
    let gray = new cv.Mat();
    if (src.channels() > 1) {
      cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
    } else {
      gray = src.clone();
    }
    tempMats.push(gray);

    // 2. Apply erode-subtract to the image (matching Python preprocessing)
    const kernel = cv.getStructuringElement(cv.MORPH_RECT, new cv.Size(5, 5));
    tempMats.push(kernel);

    const eroded = new cv.Mat();
    cv.erode(gray, eroded, kernel, new cv.Point(-1, -1), 5);
    tempMats.push(eroded);

    const imageErodedSub = new cv.Mat();
    cv.subtract(gray, eroded, imageErodedSub);
    tempMats.push(imageErodedSub);

    // 3. Divide image into 4 quadrants (Python: midh = h//3, midw = w//2)
    const midW = Math.floor(src.cols / 2);
    const midH = Math.floor(src.rows / 3);  // HEIGHT divided by 3 (matching Python)
    const quadrants = [
      { origin: [0, 0], width: midW, height: midH },           // Top-left
      { origin: [midW, 0], width: src.cols - midW, height: midH },  // Top-right
      { origin: [0, midH], width: midW, height: src.rows - midH },  // Bottom-left
      { origin: [midW, midH], width: src.cols - midW, height: src.rows - midH }  // Bottom-right
    ];

    const centres = [];
    const maxMatchingValues = [];

    // 4. Multi-scale template matching in each quadrant
    // Python defaults: marker_rescale_range=[60, 130], marker_rescale_steps=15
    const rescaleRange = markerOptions.marker_rescale_range || [60, 130];
    const rescaleSteps = markerOptions.marker_rescale_steps || 15;
    const descentPerStep = (rescaleRange[1] - rescaleRange[0]) / rescaleSteps;
    const minMatchingThreshold = markerOptions.min_matching_threshold || 0.2;

    for (let q = 0; q < 4; q++) {
      const quad = quadrants[q];
      const rect = new cv.Rect(quad.origin[0], quad.origin[1], quad.width, quad.height);
      const roi = imageErodedSub.roi(rect);
      tempMats.push(roi);

      let maxT = -1;
      let bestMatchLoc = null;
      let bestScale = 1.0;

      // Multi-scale search from large to small
      for (let r0 = rescaleRange[1]; r0 >= rescaleRange[0]; r0 -= descentPerStep) {
        const s = r0 / 100.0;

        // Resize marker
        const rescaledMarker = new cv.Mat();
        const newSize = new cv.Size(
          Math.round(markerImage.cols * s),
          Math.round(markerImage.rows * s)
        );
        cv.resize(markerImage, rescaledMarker, newSize, 0, 0, cv.INTER_AREA);

        // Skip if marker is larger than ROI
        if (rescaledMarker.cols > roi.cols || rescaledMarker.rows > roi.rows) {
          rescaledMarker.delete();
          continue;
        }

        // Template matching
        const result = new cv.Mat();
        cv.matchTemplate(roi, rescaledMarker, result, cv.TM_CCOEFF_NORMED);

        const minMax = cv.minMaxLoc(result);
        const currentMaxT = minMax.maxVal;

        if (currentMaxT > maxT) {
          maxT = currentMaxT;
          bestMatchLoc = minMax.maxLoc;
          bestScale = s;
        }

        result.delete();
        rescaledMarker.delete();
      }

      // Validate match
      if (maxT < minMatchingThreshold) {
        throw new Error(`Marker not found in quadrant ${q + 1}, max matching: ${maxT.toFixed(3)}`);
      }

      // Calculate marker center in original image coordinates
      const markerWidth = markerImage.cols * bestScale;
      const markerHeight = markerImage.rows * bestScale;
      const centerX = quad.origin[0] + bestMatchLoc.x + markerWidth / 2;
      const centerY = quad.origin[1] + bestMatchLoc.y + markerHeight / 2;

      centres.push({ x: centerX, y: centerY });
      maxMatchingValues.push(maxT);
    }

    // 5. Validate matching variation
    const maxMatchingVariation = markerOptions.max_matching_variation || 0.41;
    const matchingDiff = Math.max(...maxMatchingValues) - Math.min(...maxMatchingValues);
    if (matchingDiff > maxMatchingVariation) {
      console.warn(`[Worker] High matching variation: ${matchingDiff.toFixed(3)} > ${maxMatchingVariation}`);
    }

    // 6. Order points (TL, TR, BR, BL)
    const orderedCentres = orderPoints(centres);

    // 7. Calculate output dimensions
    let outputWidth, outputHeight;
    if (templatePageDimensions && Array.isArray(templatePageDimensions) && templatePageDimensions.length === 2) {
      outputWidth = templatePageDimensions[0];
      outputHeight = templatePageDimensions[1];
    } else {
      const [tl, tr, br, bl] = orderedCentres;
      const widthTop = Math.hypot(tr.x - tl.x, tr.y - tl.y);
      const widthBottom = Math.hypot(br.x - bl.x, br.y - bl.y);
      outputWidth = Math.max(widthTop, widthBottom);

      const heightLeft = Math.hypot(bl.x - tl.x, bl.y - tl.y);
      const heightRight = Math.hypot(br.x - tr.x, br.y - tr.y);
      outputHeight = Math.max(heightLeft, heightRight);
    }

    // 8. Compute perspective transform
    const srcPoints = cv.matFromArray(4, 1, cv.CV_32FC2, [
      orderedCentres[0].x, orderedCentres[0].y,
      orderedCentres[1].x, orderedCentres[1].y,
      orderedCentres[2].x, orderedCentres[2].y,
      orderedCentres[3].x, orderedCentres[3].y
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

    // 9. Apply perspective transform
    const corrected = new cv.Mat();
    cv.warpPerspective(
      src,
      corrected,
      M,
      new cv.Size(outputWidth, outputHeight),
      cv.INTER_LINEAR,
      cv.BORDER_CONSTANT,
      new cv.Scalar(255, 255, 255, 255)
    );

    // 10. Create visualization
    const visualization = src.clone();
    orderedCentres.forEach((center, idx) => {
      cv.circle(
        visualization,
        new cv.Point(center.x, center.y),
        10,
        [0, 255, 0, 255],
        -1
      );

      cv.putText(
        visualization,
        String(idx + 1),
        new cv.Point(center.x + 15, center.y + 15),
        cv.FONT_HERSHEY_SIMPLEX,
        1,
        [255, 0, 0, 255],
        2
      );
    });

    return {
      corrected,
      visualization,
      corners: orderedCentres
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
 * Order 4 points: top-left, top-right, bottom-right, bottom-left
 * Python order_points logic
 */
function orderPoints(points) {
  // Calculate centroid
  const centerX = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const centerY = points.reduce((sum, p) => sum + p.y, 0) / points.length;

  // Classify corners
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
 * 排序四個角點（左上、右上、右下、左下）
 */
/**
 * Calculate global threshold from all bubble mean values
 * Based on Python's get_global_threshold() - finds the largest gap in sorted values
 */
function calculateGlobalThreshold(values, looseness = 4) {
  if (values.length === 0) return 255;
  if (values.length < 3) return Math.max(...values);

  const sorted = [...values].sort((a, b) => a - b);
  const MIN_JUMP = 25;

  // Python: ls = (looseness + 1) // 2
  const ls = Math.floor((looseness + 1) / 2);
  const l = sorted.length - ls;

  let maxJump = MIN_JUMP;
  let threshold = 255;

  // Find the largest gap between values with looseness
  // Python: jump = q_vals[i + ls] - q_vals[i - ls]
  for (let i = ls; i < l; i++) {
    const jump = sorted[i + ls] - sorted[i - ls];

    if (jump > maxJump) {
      maxJump = jump;
      threshold = sorted[i - ls] + jump / 2;
    }
  }

  return threshold;
}

/**
 * Calculate local threshold for a question strip (one row of bubbles)
 * Based on Python's get_local_threshold()
 */
function calculateLocalThreshold(stripValues, globalThreshold, noOutliers = false) {
  if (stripValues.length === 0) return globalThreshold;
  if (stripValues.length < 3) {
    const range = Math.max(...stripValues) - Math.min(...stripValues);
    return range < 25 ? globalThreshold : (Math.max(...stripValues) + Math.min(...stripValues)) / 2;
  }

  const sorted = [...stripValues].sort((a, b) => a - b);
  const MIN_JUMP = 25;
  const CONFIDENT_SURPLUS = 5;

  let maxJump = MIN_JUMP;
  let threshold = 255;

  // Find the largest gap between consecutive values
  for (let i = 1; i < sorted.length - 1; i++) {
    const jump = sorted[i + 1] - sorted[i - 1];
    if (jump > maxJump) {
      maxJump = jump;
      threshold = sorted[i - 1] + jump / 2;
    }
  }

  const confidentJump = MIN_JUMP + CONFIDENT_SURPLUS;

  // If not confident in local threshold, use global (Python-style)
  if (maxJump < confidentJump) {
    if (noOutliers) {
      // All Black or All White case - use global threshold
      threshold = globalThreshold;
    }
    // else: Low confidence but has outliers - keep the calculated threshold
  }

  return threshold;
}

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

    // QR Code 區域需要較大的範圍
    const qrSize = Math.max(boxW, boxH) * 50;
    const x1 = Math.max(0, x - Math.floor(qrSize / 2));
    const y1 = Math.max(0, y - Math.floor(qrSize / 2));
    const x2 = Math.min(img.cols, x + Math.floor(qrSize / 2));
    const y2 = Math.min(img.rows, y + Math.floor(qrSize / 2));

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

    // 3. Initialize all question fields with empty arrays
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

    // 4. Calculate mean grayscale values for all bubbles (Python-style detection)
    // Lower mean value = darker = more filled
    const bubbleData = [];
    const stripData = {}; // Group by fieldLabel (question)

    for (const expectedBubble of expectedBubbles) {
      const { x, y, width, height, fieldLabel, fieldValue } = expectedBubble;

      // Create ROI rect for this bubble
      const roi = new cv.Rect(
        Math.max(0, x),
        Math.max(0, y),
        width,
        height
      );

      // Ensure ROI is within image bounds
      if (roi.x + roi.width > gray.cols) {
        roi.width = gray.cols - roi.x;
      }
      if (roi.y + roi.height > gray.rows) {
        roi.height = gray.rows - roi.y;
      }

      if (roi.width <= 0 || roi.height <= 0) {
        console.warn(`[Worker] Invalid ROI for bubble ${fieldLabel}=${fieldValue}:`, roi);
        continue;
      }

      // Extract ROI from grayscale image
      const grayRoi = gray.roi(roi);

      // Calculate mean grayscale value (same as Python's cv2.mean()[0])
      const meanValue = cv.mean(grayRoi)[0];
      grayRoi.delete();

      const bubble = {
        x, y, width, height,
        fieldLabel, fieldValue,
        meanValue
      };

      bubbleData.push(bubble);

      // Group by fieldLabel for per-strip threshold calculation
      if (!stripData[fieldLabel]) {
        stripData[fieldLabel] = [];
      }
      stripData[fieldLabel].push(bubble);
    }

    // 5. Calculate global threshold from all bubble mean values
    const allMeanValues = bubbleData.map(b => b.meanValue);
    const globalThreshold = calculateGlobalThreshold(allMeanValues, 4);

    // 5.1 Calculate standard deviation for each question strip (Python-style)
    const allStdValues = [];
    for (const fieldLabel in stripData) {
      const stripMeanValues = stripData[fieldLabel].map(b => b.meanValue);
      const mean = stripMeanValues.reduce((a, b) => a + b, 0) / stripMeanValues.length;
      const variance = stripMeanValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / stripMeanValues.length;
      const std = Math.sqrt(variance);
      allStdValues.push(std);
    }

    // 5.2 Calculate global standard deviation threshold
    const globalStdThreshold = calculateGlobalThreshold(allStdValues, 1);

    // 6. Detect marked bubbles using per-strip local threshold
    const visualizationData = [];
    let questionNum = 0;
    let stripIndex = 0;

    for (const fieldLabel in stripData) {
      const stripBubbles = stripData[fieldLabel];
      const stripMeanValues = stripBubbles.map(b => b.meanValue);

      // Calculate standard deviation for this strip
      const mean = stripMeanValues.reduce((a, b) => a + b, 0) / stripMeanValues.length;
      const variance = stripMeanValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / stripMeanValues.length;
      const stripStd = Math.sqrt(variance);

      // Check if this strip has no outliers (Python-style)
      const noOutliers = stripStd < globalStdThreshold;

      // Calculate local threshold for this question strip
      const localThreshold = calculateLocalThreshold(stripMeanValues, globalThreshold, noOutliers);

      questionNum++;
      stripIndex++;

      // Detect marked bubbles: threshold > meanValue (lower value = darker = filled)
      for (const bubble of stripBubbles) {
        const isFilled = localThreshold > bubble.meanValue;

        if (isFilled) {
          answers[bubble.fieldLabel].push(bubble.fieldValue);
        }

        // Store for visualization
        visualizationData.push({
          ...bubble,
          isFilled,
          threshold: localThreshold
        });
      }
    }

    // 建立視覺化結果 - 只標記填塗的格子，不顯示對錯
    const visualization = correctedMat.clone();

    for (const data of visualizationData) {
      const { x, y, width, height, fieldLabel, fieldValue, isFilled, meanValue, threshold } = data;

      const studentAnswers = answers[fieldLabel] || [];
      const isSelected = studentAnswers.includes(fieldValue);

      // 選擇顏色：只區分填塗/未填塗，不顯示對錯
      let color;
      if (isSelected) {
        color = [0, 255, 0, 255];  // 綠色 - 已填塗
      } else {
        color = [200, 200, 200, 255];  // 淺灰色 - 未填塗
      }

      // Draw rectangle at bubble position
      cv.rectangle(
        visualization,
        new cv.Point(x, y),
        new cv.Point(x + width, y + height),
        color,
        2
      );

      // 如果已填塗，標記平均值
      if (isSelected) {
        cv.putText(
          visualization,
          `${Math.round(meanValue)}`,
          new cv.Point(x + 5, y + height - 5),
          cv.FONT_HERSHEY_SIMPLEX,
          0.4,
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

    // 3. 透視校正 - 使用模板的 pageDimensions 和 CropOnMarkers 設定
    const templatePageDimensions = currentTemplate ? currentTemplate.pageDimensions : null;

    // Extract CropOnMarkers options from template
    let markerOptions = {};
    if (currentTemplate && currentTemplate.preProcessors) {
      const cropOnMarkersConfig = currentTemplate.preProcessors.find(
        p => p.name === 'CropOnMarkers'
      );
      if (cropOnMarkersConfig && cropOnMarkersConfig.options) {
        markerOptions = cropOnMarkersConfig.options;
      }
    }

    const perspectiveResult = correctPerspectiveWithMarkers(src, templatePageDimensions, markerOptions);
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
      perspectiveResult: matToImageData(perspectiveResult.visualization),
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



/**
 * Generates a concentric circle marker image (black-white-black circles) as a grayscale cv.Mat.
 * This marker is used for automatic alignment and cropping of OMR sheets.
 * The marker consists of three concentric circles:
 * - Outer circle (black)
 * - Middle circle (white, 70% of marker radius by default)
 * - Inner circle (black, 40% of marker radius by default)
 *
 * @param {number} markerSize - Size of the marker in pixels (width and height).
 * @param {object} options - Configuration object containing marker ratios.
 * @param {number} [options.marker_middle_circle_ratio=0.7] - Ratio for the middle white circle.
 * @param {number} [options.marker_inner_circle_ratio=0.4] - Ratio for the inner black circle.
 * @returns {cv.Mat} - A 1-channel (grayscale) cv.Mat representing the marker.
 */
function generateDefaultMarkerImage(markerSize, options = {}) {
  const middleCircleRatio = options.marker_middle_circle_ratio || 0.7;
  const innerCircleRatio = options.marker_inner_circle_ratio || 0.4;

  if (markerSize <= 0) {
    throw new Error('Marker size must be a positive integer.');
  }

  // Create a white background, 1-channel (grayscale) image
  const markerImg = new cv.Mat(markerSize, markerSize, cv.CV_8UC1, new cv.Scalar(255));
  const center = markerSize / 2;
  const outerRadius = markerSize / 2;

  // Draw outer circle (black)
  cv.circle(markerImg, new cv.Point(center, center), outerRadius, new cv.Scalar(0), -1);

  // Draw middle circle (white)
  const middleRadius = Math.floor(outerRadius * middleCircleRatio);
  cv.circle(markerImg, new cv.Point(center, center), middleRadius, new cv.Scalar(255), -1);

  // Draw inner circle (black)
  const innerRadius = Math.floor(outerRadius * innerCircleRatio);
  cv.circle(markerImg, new cv.Point(center, center), innerRadius, new cv.Scalar(0), -1);

  return markerImg;
}
