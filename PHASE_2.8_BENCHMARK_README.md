# Phase 2.8: OCR Provider Benchmark 使用說明

## 目標
比較 Tesseract OCR 與 Gemini Vision OCR 在保險文件截圖上的準確度。

## 測試資料
- **測試圖片**: `C:\Users\user\Desktop\cfa7f45f-625b-4f40-bb3e-d095b30b3694.jpg`
- **文件類型**: 保誠保險客戶資料頁面

## Ground Truth (驗收標準)
從截圖中應能準確提取以下欄位：

| 欄位 | 預期值 |
|------|--------|
| name | YIU CHUN NING |
| phone | 85296730153 |
| email | Yiuchunning@gmail.com |
| policy_number | 02817117 |
| address | 香港九龍黃大仙竹薯南邨趣薯樓644室 |

## 成功標準
Gemini Vision 至少準確提取 **4/5** 個關鍵欄位（姓名、電話、Email、保單號碼）。

## 執行步驟

### 1. 確認環境設定

檢查 `.env` 檔案是否包含 Gemini API Key：

```bash
GEMINI_API_KEY=your_actual_api_key_here
```

### 2. 確認 Tesseract 已安裝

Windows 環境需安裝 Tesseract OCR：
- 下載：https://github.com/UB-Mannheim/tesseract/wiki
- 安裝後確認路徑 (通常是 `C:\Program Files\Tesseract-OCR\tesseract.exe`)
- 需要包含中文語言包 (`chi_tra.traineddata`)

### 3. 執行 Benchmark

```bash
cd buildway-ai-core-main
python scripts/run_ocr_benchmark.py
```

或指定自訂圖片路徑：

```bash
python scripts/run_ocr_benchmark.py "C:\path\to\your\image.jpg"
```

### 4. 查看結果

Benchmark 會產生：
1. **終端輸出**: 即時顯示比較結果
2. **報告檔案**: `PHASE_2.8_OCR_BENCHMARK_REPORT.md`

報告包含：
- 整體準確度比較
- 欄位逐一比較
- 原始 OCR 文字輸出
- 結構化提取結果

## 疑難排解

### Tesseract 提取結果為空

可能原因：
1. Tesseract 未正確安裝
2. 中文語言包缺失
3. 圖片品質問題

解決方法：
```bash
# 測試 Tesseract 是否可用
tesseract --version
tesseract --list-langs  # 確認有 chi_tra 和 eng
```

### Gemini API 錯誤

可能原因：
1. API Key 未設定或錯誤
2. API 配額用盡
3. 網路連線問題

解決方法：
- 檢查 `.env` 檔案
- 確認 API Key 有效且有配額
- 檢查網路連線

### 圖片路徑錯誤

確保圖片路徑正確且檔案存在：
```bash
# 檢查檔案是否存在
python -c "from pathlib import Path; print(Path(r'C:\Users\user\Desktop\cfa7f45f-625b-4f40-bb3e-d095b30b3694.jpg').exists())"
```

## 技術細節

### Tesseract 處理流程
1. 載入原始圖片
2. 產生 4 種前處理變體：
   - `original`: 原始圖片
   - `cropped`: 裁剪文件區域
   - `enhanced`: 影像增強（3x resize, grayscale, contrast, sharpen）
   - `cropped_enhanced`: 裁剪 + 增強
3. 對每個變體執行 OCR
4. 選擇文字量最多、包含最多電話/email pattern 的結果

### Gemini Vision 處理流程
1. 載入圖片為 bytes
2. 調用 Gemini API (模型: `gemini-2.0-flash`)
3. 使用自訂 prompt 提取保險文件資訊
4. 回傳結構化文字

### 欄位提取邏輯
使用 regex patterns 從 OCR 原文提取結構化欄位：
- **Name**: 英文大寫姓名模式
- **Phone**: 香港電話號碼格式 (852-XXXXXXXX)
- **Email**: 標準 email 格式
- **Policy Number**: 8位數字
- **Address**: 香港地址關鍵字（香港/九龍/新界）

## 預期結果

### Tesseract
- **優勢**: 本地執行，免費，支援中英文
- **挑戰**: 截圖雜訊、表格結構、文字方向

### Gemini Vision
- **優勢**: 理解上下文，處理複雜版面，多語言
- **挑戰**: API 成本，需要網路連線

## 後續步驟

根據 benchmark 結果：

1. **Gemini 明顯優於 Tesseract** → 考慮整合到生產環境
2. **兩者差異不大** → 優先使用 Tesseract (免費 + 本地)
3. **兩者都不理想** → 需要改善圖片前處理或調整 prompt

## 相關檔案

- `scripts/run_ocr_benchmark.py` - Benchmark 執行腳本
- `core/ocr/benchmark.py` - 驗證與比較框架
- `core/ocr/image_preprocessing.py` - 圖片前處理
- `core/ocr/result_selector.py` - 最佳結果選擇器
- `apps/streamlit_group_training/services/ocr_service.py` - Gemini Vision 整合
