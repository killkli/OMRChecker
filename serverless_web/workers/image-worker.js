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

  // 回傳給主執行緒
  READY: 'ready',
  PROGRESS: 'progress',
  RESULT: 'result',
  ERROR: 'error'
};

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

    // 3. 透視校正
    sendProgress(40, '執行透視校正...', id);
    const perspectiveResult = correctPerspective(src);
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
function correctPerspective(src) {
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

    const widthTop = Math.hypot(tr.x - tl.x, tr.y - tl.y);
    const widthBottom = Math.hypot(br.x - bl.x, br.y - bl.y);
    const maxWidth = Math.max(widthTop, widthBottom);

    const heightLeft = Math.hypot(bl.x - tl.x, bl.y - tl.y);
    const heightRight = Math.hypot(br.x - tr.x, br.y - tr.y);
    const maxHeight = Math.max(heightLeft, heightRight);

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
      maxWidth, 0,
      maxWidth, maxHeight,
      0, maxHeight
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
      new cv.Size(maxWidth, maxHeight)
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
  const points = [];
  for (let i = 0; i < approx.rows; i++) {
    points.push({
      x: approx.data32F[i * 2],
      y: approx.data32F[i * 2 + 1]
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
 * 檢測並解析答案
 */
function detectAndParseAnswers(correctedMat, template) {
  const tempMats = [];

  try {
    // 1. 轉換為灰階
    const gray = new cv.Mat();
    cv.cvtColor(correctedMat, gray, cv.COLOR_RGBA2GRAY);
    tempMats.push(gray);

    // 2. 二值化
    const binary = new cv.Mat();
    cv.threshold(gray, binary, 0, 255, cv.THRESH_BINARY_INV | cv.THRESH_OTSU);
    tempMats.push(binary);

    // 3. 查找輪廓
    const contours = new cv.MatVector();
    const hierarchy = new cv.Mat();
    cv.findContours(
      binary,
      contours,
      hierarchy,
      cv.RETR_EXTERNAL,
      cv.CHAIN_APPROX_SIMPLE
    );
    tempMats.push(hierarchy);

    // 4. 過濾標記輪廓
    const bubbles = [];
    const minArea = template.bubble.minArea;
    const maxArea = template.bubble.maxArea;

    for (let i = 0; i < contours.size(); i++) {
      const contour = contours.get(i);
      const area = cv.contourArea(contour);

      if (area >= minArea && area <= maxArea) {
        const rect = cv.boundingRect(contour);
        const aspectRatio = rect.width / rect.height;

        // 檢查長寬比（應接近 1.0 為圓形）
        if (aspectRatio >= 0.7 && aspectRatio <= 1.3) {
          bubbles.push({
            contour: contour.clone(),
            rect,
            area
          });
        }
      }

      contour.delete();
    }
    contours.delete();

    // 5. 按位置排序（由上到下，由左到右）
    bubbles.sort((a, b) => {
      const yDiff = a.rect.y - b.rect.y;
      if (Math.abs(yDiff) > 20) {  // 不同行
        return yDiff;
      }
      return a.rect.x - b.rect.x;  // 同一行，比較 x
    });

    // 6. 計算填充率並解析答案
    const answers = {};
    const questionsPerRow = template.layout.questionsPerRow;
    const optionsPerQuestion = template.layout.optionsPerQuestion;

    bubbles.forEach((bubble, idx) => {
      const questionNo = Math.floor(idx / optionsPerQuestion) + 1;
      const optionIdx = idx % optionsPerQuestion;
      const optionLabel = String.fromCharCode(65 + optionIdx);  // A, B, C, D...

      // 計算填充率
      const mask = new cv.Mat.zeros(binary.rows, binary.cols, cv.CV_8U);
      const maskVector = new cv.MatVector();
      maskVector.push_back(bubble.contour);
      cv.drawContours(mask, maskVector, 0, [255, 255, 255, 255], -1);
      maskVector.delete();

      // Safe ROI operations (track all temporary Mats)
      const binaryRoi = binary.roi(bubble.rect);
      const maskRoi = mask.roi(bubble.rect);
      const andResult = binaryRoi.and(maskRoi);
      const filledPixels = cv.countNonZero(andResult);

      // Release temporary Mats
      andResult.delete();
      maskRoi.delete();
      binaryRoi.delete();

      const totalPixels = bubble.area;
      const fillRatio = filledPixels / totalPixels;

      mask.delete();

      // 判斷是否填塗（閾值可調整）
      if (fillRatio > template.detection.fillThreshold) {
        if (!answers[questionNo]) {
          answers[questionNo] = [];
        }
        answers[questionNo].push(optionLabel);
      }
    });

    // 7. 計算分數
    const scoring = calculateScore(answers, template.answers);

    // 8. 建立視覺化結果
    const visualization = correctedMat.clone();

    bubbles.forEach((bubble, idx) => {
      const questionNo = Math.floor(idx / optionsPerQuestion) + 1;
      const optionIdx = idx % optionsPerQuestion;
      const optionLabel = String.fromCharCode(65 + optionIdx);

      const studentAnswers = answers[questionNo] || [];
      const isSelected = studentAnswers.includes(optionLabel);
      const correctAnswer = template.answers[questionNo];
      const isCorrect = correctAnswer && correctAnswer.includes(optionLabel);

      // 選擇顏色
      let color;
      if (isSelected && isCorrect) {
        color = [0, 255, 0, 255];  // 綠色 - 正確
      } else if (isSelected && !isCorrect) {
        color = [255, 0, 0, 255];  // 紅色 - 錯誤
      } else if (!isSelected && isCorrect) {
        color = [0, 0, 255, 255];  // 藍色 - 應選但未選
      } else {
        color = [128, 128, 128, 255];  // 灰色 - 未選
      }

      // Safe MatVector creation and cleanup
      const contourVector = new cv.MatVector();
      contourVector.push_back(bubble.contour);
      cv.drawContours(
        visualization,
        contourVector,
        0,
        color,
        2
      );
      contourVector.delete();
    });

    // 清理 bubble contours
    bubbles.forEach(b => b.contour.delete());

    return {
      answers,
      scoring,
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

console.log('[Worker] Image Worker 已載入');
