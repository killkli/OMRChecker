/**
 * Config and Evaluation Parser
 * 解析 config.json 和 evaluation.json 檔案
 */

class ConfigParser {
  /**
   * 解析 config.json
   * @param {Object} config - Config JSON 物件
   * @returns {Object} 處理後的設定
   */
  static parseConfig(config) {
    if (!config) {
      return this.getDefaultConfig();
    }

    return {
      // 影像處理參數
      imageProcessing: {
        threshold: config.threshold || 127,
        thresholdType: config.thresholdType || 'ADAPTIVE',
        blurKernelSize: config.blurKernelSize || 5,
        morphKernelSize: config.morphKernelSize || 3,
        adaptiveThresholdBlockSize: config.adaptiveThresholdBlockSize || 11,
        adaptiveThresholdC: config.adaptiveThresholdC || 2,
        ...config.imageProcessing
      },

      // 輪廓檢測參數
      contourDetection: {
        minArea: config.minArea || 100,
        maxArea: config.maxArea || 10000,
        epsilon: config.epsilon || 0.02,
        ...config.contourDetection
      },

      // 透視校正參數
      perspectiveCorrection: {
        enabled: config.enablePerspectiveCorrection !== false,
        outputWidth: config.outputWidth || 850,
        outputHeight: config.outputHeight || 1202,
        ...config.perspectiveCorrection
      },

      // 答案檢測參數
      answerDetection: {
        fillThreshold: config.fillThreshold || 0.4,
        minFillRatio: config.minFillRatio || 0.3,
        maxFillRatio: config.maxFillRatio || 0.9,
        ...config.answerDetection
      },

      // 調優參數
      tuning: {
        debugMode: config.debugMode || false,
        saveIntermediateImages: config.saveIntermediateImages || false,
        ...config.tuning
      },

      // 其他參數
      ...config
    };
  }

  /**
   * 取得預設設定
   */
  static getDefaultConfig() {
    return {
      imageProcessing: {
        threshold: 127,
        thresholdType: 'ADAPTIVE',
        blurKernelSize: 5,
        morphKernelSize: 3,
        adaptiveThresholdBlockSize: 11,
        adaptiveThresholdC: 2
      },
      contourDetection: {
        minArea: 100,
        maxArea: 10000,
        epsilon: 0.02
      },
      perspectiveCorrection: {
        enabled: true,
        outputWidth: 850,
        outputHeight: 1202
      },
      answerDetection: {
        fillThreshold: 0.4,
        minFillRatio: 0.3,
        maxFillRatio: 0.9
      },
      tuning: {
        debugMode: false,
        saveIntermediateImages: false
      }
    };
  }

  /**
   * 驗證設定
   */
  static validateConfig(config) {
    const errors = [];

    if (config.imageProcessing) {
      if (config.imageProcessing.threshold < 0 || config.imageProcessing.threshold > 255) {
        errors.push('threshold 必須在 0-255 之間');
      }
      if (config.imageProcessing.blurKernelSize % 2 === 0) {
        errors.push('blurKernelSize 必須是奇數');
      }
    }

    if (config.answerDetection) {
      if (config.answerDetection.fillThreshold < 0 || config.answerDetection.fillThreshold > 1) {
        errors.push('fillThreshold 必須在 0-1 之間');
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}

class EvaluationParser {
  /**
   * 解析 evaluation.json
   * @param {Object} evaluation - Evaluation JSON 物件
   * @returns {Object} 處理後的評分標準
   */
  static parseEvaluation(evaluation) {
    if (!evaluation) {
      return null;
    }

    return {
      // 答案鍵
      answerKey: evaluation.answerKey || evaluation.answers || {},

      // 評分規則
      scoring: {
        totalQuestions: evaluation.totalQuestions || Object.keys(evaluation.answerKey || {}).length,
        pointsPerQuestion: evaluation.pointsPerQuestion || 5,
        totalPoints: evaluation.totalPoints || 100,
        passingScore: evaluation.passingScore || 60,
        partialCredit: evaluation.partialCredit || false,
        ...evaluation.scoring
      },

      // 標記方案
      markingScheme: {
        correctColor: evaluation.correctColor || [0, 255, 0], // 綠色
        incorrectColor: evaluation.incorrectColor || [255, 0, 0], // 紅色
        unansweredColor: evaluation.unansweredColor || [128, 128, 128], // 灰色
        partialColor: evaluation.partialColor || [0, 0, 255], // 藍色
        ...evaluation.markingScheme
      },

      // 選項設定
      options: {
        allowMultipleAnswers: evaluation.allowMultipleAnswers || false,
        requireAllAnswers: evaluation.requireAllAnswers || false,
        negativeMarking: evaluation.negativeMarking || false,
        negativePoints: evaluation.negativePoints || 0,
        ...evaluation.options
      },

      // 其他參數
      ...evaluation
    };
  }

  /**
   * 評分
   * @param {Object} detectedAnswers - 檢測到的答案
   * @param {Object} evaluation - 評分標準
   * @returns {Object} 評分結果
   */
  static gradeAnswers(detectedAnswers, evaluation) {
    if (!evaluation || !evaluation.answerKey) {
      return this.getDefaultGradeResult(detectedAnswers);
    }

    const answerKey = evaluation.answerKey;
    const scoring = evaluation.scoring || {};
    const options = evaluation.options || {};

    let correctCount = 0;
    let incorrectCount = 0;
    let unansweredCount = 0;
    let partialCount = 0;
    const detailedResults = {};

    // 遍歷每個題目
    for (const [questionId, correctAnswer] of Object.entries(answerKey)) {
      const studentAnswer = detectedAnswers[questionId];

      if (!studentAnswer || studentAnswer.length === 0) {
        // 未作答
        unansweredCount++;
        detailedResults[questionId] = {
          correct: false,
          studentAnswer: [],
          correctAnswer: Array.isArray(correctAnswer) ? correctAnswer : [correctAnswer],
          status: 'unanswered'
        };
      } else {
        // 比較答案
        const correctAnswerArray = Array.isArray(correctAnswer) ? correctAnswer : [correctAnswer];
        const studentAnswerArray = Array.isArray(studentAnswer) ? studentAnswer : [studentAnswer];

        // 檢查是否完全正確
        const isCorrect = this.compareAnswers(studentAnswerArray, correctAnswerArray);

        if (isCorrect) {
          correctCount++;
          detailedResults[questionId] = {
            correct: true,
            studentAnswer: studentAnswerArray,
            correctAnswer: correctAnswerArray,
            status: 'correct'
          };
        } else {
          // 檢查部分正確（如果允許）
          if (scoring.partialCredit && studentAnswerArray.some(a => correctAnswerArray.includes(a))) {
            partialCount++;
            detailedResults[questionId] = {
              correct: false,
              studentAnswer: studentAnswerArray,
              correctAnswer: correctAnswerArray,
              status: 'partial'
            };
          } else {
            incorrectCount++;
            detailedResults[questionId] = {
              correct: false,
              studentAnswer: studentAnswerArray,
              correctAnswer: correctAnswerArray,
              status: 'incorrect'
            };
          }
        }
      }
    }

    // 計算分數
    const totalQuestions = Object.keys(answerKey).length;
    const pointsPerQuestion = scoring.pointsPerQuestion || 5;
    let score = correctCount * pointsPerQuestion;

    // 部分得分
    if (scoring.partialCredit && partialCount > 0) {
      score += partialCount * pointsPerQuestion * 0.5; // 部分正確給一半分數
    }

    // 負分
    if (options.negativeMarking && incorrectCount > 0) {
      score -= incorrectCount * (options.negativePoints || 0);
    }

    // 確保分數不為負
    score = Math.max(0, score);
    const totalPoints = scoring.totalPoints || (totalQuestions * pointsPerQuestion);
    const percentage = (score / totalPoints) * 100;

    return {
      totalQuestions,
      correctCount,
      incorrectCount,
      unansweredCount,
      partialCount,
      score: Math.round(score * 10) / 10, // 四捨五入到小數點一位
      totalPoints,
      percentage: Math.round(percentage * 10) / 10,
      passed: score >= (scoring.passingScore || 60),
      detailedResults
    };
  }

  /**
   * 比較答案
   */
  static compareAnswers(studentAnswer, correctAnswer) {
    if (studentAnswer.length !== correctAnswer.length) {
      return false;
    }

    const sortedStudent = [...studentAnswer].sort();
    const sortedCorrect = [...correctAnswer].sort();

    return sortedStudent.every((ans, i) => ans === sortedCorrect[i]);
  }

  /**
   * 取得預設評分結果（沒有 evaluation 時）
   */
  static getDefaultGradeResult(detectedAnswers) {
    const totalQuestions = Object.keys(detectedAnswers).length;
    const answeredCount = Object.values(detectedAnswers).filter(a => a && a.length > 0).length;
    const unansweredCount = totalQuestions - answeredCount;

    return {
      totalQuestions,
      correctCount: 0,
      incorrectCount: 0,
      unansweredCount,
      partialCount: 0,
      score: 0,
      totalPoints: 0,
      percentage: 0,
      passed: false,
      detailedResults: {}
    };
  }

  /**
   * 驗證評分標準
   */
  static validateEvaluation(evaluation) {
    const errors = [];

    if (!evaluation.answerKey && !evaluation.answers) {
      errors.push('缺少答案鍵 (answerKey 或 answers)');
    }

    if (evaluation.scoring) {
      if (evaluation.scoring.pointsPerQuestion <= 0) {
        errors.push('pointsPerQuestion 必須大於 0');
      }
      if (evaluation.scoring.totalPoints < 0) {
        errors.push('totalPoints 不能為負');
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}

// 如果在瀏覽器環境
if (typeof window !== 'undefined') {
  window.ConfigParser = ConfigParser;
  window.EvaluationParser = EvaluationParser;
}
