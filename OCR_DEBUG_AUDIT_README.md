# OCR Emergency Audit Tool 使用說明

## 目的

**不修改任何功能，只做診斷。**

此工具用於診斷 Phase 2.7 OCR Accuracy Upgrade 的每個步驟，輸出所有中間結果，以便人工檢查哪一個環節出錯。

---

## 功能

### 1. 輸出四種預處理圖片到 `debug/ocr/`

- `original.png` - 原圖
- `cropped.png` - 裁剪黑邊後
- `enhanced.png` - 影像增強（3x upscale + grayscale + contrast + sharpen）
- `cropped_enhanced.png` - 裁剪 + 增強（最佳組合）

### 2. 顯示每張圖尺寸

- `width x height` 顯示在 Streamlit UI
- 可檢查 crop 是否裁得太小或太大

### 3. 對四張圖各自跑 OCR

輸出四個文字檔到 `debug/ocr/`：

- `original_text.txt`
- `cropped_text.txt`
- `enhanced_text.txt`
- `cropped_enhanced_text.txt`

### 4. 顯示每個 OCR 結果的 Quality Score

計算方式：
- 電話匹配 × 10 分
- Email 匹配 × 10 分
- 日期匹配 × 3 分
- Key-Value 結構 × 2 分
- 數字出現 (上限 20 分)
- 中英混合 +5 分

### 5. Best Selector 選擇結果

顯示最終採用哪一個 OCR 結果（score 最高）

### 6. 驗證預期資料

檢查 OCR 原文是否包含：
- 姓名: `YIU CHUN NING`
- 電話: `85296730153`
- Email: `Yiuchunning@gmail.com`

### 7. 產生 `audit_report.md`

診斷四個環節：

1. **Crop 是否裁錯**
   - 裁剪後 < 30% → 可能裁錯
   - 裁剪後 > 95% → 未裁剪
   - 其他 → 正常

2. **Best Selector 是否選錯**
   - 檢查是否選擇了 score 最高的 variant

3. **OCR Engine 是否讀錯**
   - 檢查預期資料是否在 OCR 原文中

4. **DeepSeek Extraction 是否出錯**
   - （此工具不執行 DeepSeek，僅診斷 OCR 原文）

---

## 使用方法

### 方法 1: 直接執行 Streamlit App

```bash
cd "c:\Users\user\Desktop\Buildway AI Group Training System\buildway-ai-core-main"
streamlit run apps/streamlit_group_training/ocr_debug_audit.py
```

### 方法 2: 從主 App 呼叫（需要整合）

暫時使用方法 1 獨立執行。

---

## 輸出檔案結構

```
debug/ocr/
├── original.png
├── cropped.png
├── enhanced.png
├── cropped_enhanced.png
├── original_text.txt
├── cropped_text.txt
├── enhanced_text.txt
├── cropped_enhanced_text.txt
└── audit_report.md
```

---

## 測試步驟

1. 啟動 OCR Debug Audit Tool
2. 上傳保單截圖（包含 YIU CHUN NING / 85296730153 / Yiuchunning@gmail.com）
3. 點擊「開始 OCR Audit」
4. 檢查 Streamlit UI 顯示的四個 OCR 結果
5. 檢查 `debug/ocr/` 目錄中的所有檔案
6. 閱讀 `audit_report.md` 診斷結論

---

## 預期結果

如果 Phase 2.7 實作正確：

- ✅ `cropped_enhanced.png` 應該是最清晰的圖片
- ✅ `cropped_enhanced_text.txt` 應該有最高的 Quality Score
- ✅ Best Selector 應該選擇 `cropped_enhanced`
- ✅ OCR 原文應該包含姓名、電話、Email

如果有問題：

- ⚠️ Crop 裁得太小 → 需要調整 `detect_and_crop_document()` 的閾值
- ⚠️ Enhanced 圖片模糊 → 需要調整 `enhance_image_for_ocr()` 的參數
- ⚠️ Best Selector 選錯 → 需要調整 `calculate_text_quality_score()` 的權重
- ⚠️ OCR 原文缺失資料 → 可能是 Tesseract 語言包問題

---

## 重要提醒

- ⚠️ 此工具**不會修改任何功能**，只輸出診斷資訊
- ⚠️ 此工具**不會執行 DeepSeek extraction**，只診斷 OCR 原文
- ⚠️ 請在本地執行，不要部署到 Streamlit Cloud
- ⚠️ 上傳的圖片和生成的檔案會儲存在本地 `debug/ocr/` 目錄

---

## 下一步

根據 `audit_report.md` 的診斷結論，決定是否需要：

1. 調整 `image_preprocessing.py` 的參數
2. 調整 `result_selector.py` 的評分權重
3. 更新 Tesseract 語言包
4. 檢查 DeepSeek prompt（如果 OCR 原文正確但結構化提取失敗）

---

## 技術細節

- **語言**: Python 3.11+
- **依賴**: Streamlit, Pillow, pytesseract, numpy
- **OCR 引擎**: Tesseract (chi_tra+eng)
- **不依賴**: DeepSeek API, Gemini API
- **不修改**: 任何現有 OCR 功能

---

## 授權

此工具僅供 Buildway AI Group Training System 內部診斷使用。
