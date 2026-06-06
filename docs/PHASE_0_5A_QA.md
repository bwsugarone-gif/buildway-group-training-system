# Phase 0.5A QA Test Checklist

## Test Environment
- Python 3.11.9
- Streamlit app running
- ChromaDB initialized
- OpenAI API configured

---

## Test Cases

### 1. MOQ Conflict Test
**Setup:**
- Index FAQ_Test.csv (contains MOQ: 500 units)
- Index Product_Catalog_Test.csv (may contain different MOQ)

**Test:**
- Query: "What is your MOQ?"
- Expected: Conflict warning if multiple MOQ values exist
- Expected: Confidence score displayed
- Expected: Source weighting applied (FAQ > catalog)

**Pass Criteria:**
- [ ] Conflict detected if applicable
- [ ] FAQ_Test.csv ranked higher than random notes
- [ ] Confidence level displayed (HIGH/MEDIUM/LOW)
- [ ] Source weight visible in debug panel

---

### 2. Garbage Pollution Test
**Setup:**
- Index FAQ_Test.csv
- Index garbage_notes.txt

**Test:**
- Query: "What is your MOQ?"
- Expected: FAQ_Test.csv results ranked higher
- Expected: garbage_notes.txt downweighted (0.3x or 0.5x)

**Pass Criteria:**
- [ ] FAQ results appear first
- [ ] Garbage file has low weighted_score
- [ ] Source weight visible in debug panel
- [ ] Final score calculation correct

---

### 3. Fake Shipping Fee Test
**Setup:**
- Index FAQ_Test.csv (no shipping fee info)

**Test:**
- Query: "How much is shipping to USA?"
- Expected: AI does NOT invent shipping fee
- Expected: AI asks for clarification

**Pass Criteria:**
- [ ] No invented pricing
- [ ] Reply asks for more info
- [ ] Confidence: LOW or MEDIUM
- [ ] No numerical estimates provided

---

### 4. Missing Data Test
**Setup:**
- Index FAQ_Test.csv

**Test:**
- Query: "What is your return policy?"
- Expected: AI states information not available
- Expected: Confidence: LOW

**Pass Criteria:**
- [ ] No hallucination
- [ ] Clear statement that info is missing
- [ ] Confidence: LOW
- [ ] Polite request for clarification

---

### 5. 中文 Query Test
**Setup:**
- Index FAQ_Test.csv

**Test:**
- Query: "你們的最小訂單量是多少？"
- Expected: Retrieves MOQ information
- Expected: Reply in appropriate language

**Pass Criteria:**
- [ ] Retrieval works with Chinese query
- [ ] Confidence score calculated
- [ ] Source weighting applied
- [ ] Reply language appropriate

---

### 6. English Query Test
**Setup:**
- Index FAQ_Test.csv

**Test:**
- Query: "What is your minimum order quantity?"
- Expected: Retrieves MOQ information
- Expected: Professional English reply

**Pass Criteria:**
- [ ] High similarity match
- [ ] Confidence: HIGH or MEDIUM
- [ ] No hallucination
- [ ] Professional tone maintained

---

### 7. Multi-Document Retrieval Test
**Setup:**
- Index FAQ_Test.csv
- Index Product_Catalog_Test.csv
- Index Reply_Templates_Test.csv

**Test:**
- Query: "Tell me about your products and MOQ"
- Expected: Retrieves from multiple sources
- Expected: Source priority applied (FAQ > catalog > template)

**Pass Criteria:**
- [ ] Multiple sources retrieved
- [ ] Correct priority ordering
- [ ] All sources visible in debug panel
- [ ] Weighted scores calculated correctly

---

## Summary Report Template

**Date:** YYYY-MM-DD  
**Tester:** [Name]  
**Environment:** [Details]

**Results:**
- Total Tests: 7
- Passed: X
- Failed: Y
- Notes: [Any observations]

**Issues Found:**
1. [Issue description]
2. [Issue description]

**Recommendations:**
- [Improvement suggestions]

---

## Expected Behavior

### Source Weighting
```
FAQ_Test.csv: weight = 1.5x
Product_Catalog_Test.csv: weight = 1.3x
Reply_Templates_Test.csv: weight = 1.1x
garbage_notes.txt: weight = 0.3x
random_notes.txt: weight = 0.5x
```

### Confidence Levels
- **HIGH (🟢)**: similarity ≥ 0.85
- **MEDIUM (🟡)**: similarity ≥ 0.65
- **LOW (🔴)**: similarity < 0.65

### Anti-Hallucination Rules
- Never invent pricing
- Never invent shipping fees
- Never invent MOQ
- Never estimate numerical values
- Ask for clarification when uncertain
