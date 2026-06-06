# RAG CRM Test Dataset

This directory contains test data for validating the RAG (Retrieval-Augmented Generation) system in Buildway AI Core's CRM module.

## Test Files Overview

### 1. FAQ_Test.csv
**Purpose:** Test structured FAQ data retrieval

**Content:**
- 23 realistic foreign trade FAQ entries
- Categories: MOQ, Shipping, Payment Terms, Lead Time, Sample Orders, Custom Packaging, Warranty, Refund, Production Time, Incoterms, Quality Control, Certifications
- Includes Auto Reply and Human Review flags

**Test Scenarios:**
- Query: "What is your MOQ?" → Should retrieve MOQ-related FAQs
- Query: "How long does shipping take?" → Should retrieve shipping time information
- Query: "What payment methods do you accept?" → Should retrieve payment terms
- Query: "Can I get samples?" → Should retrieve sample order information

**Expected Behavior:**
- CSV parser should correctly extract columns
- Chunking should preserve Q&A pairs
- Retrieval should match semantic meaning, not just keywords

---

### 2. Product_Catalog_Test.csv
**Purpose:** Test product information retrieval

**Content:**
- 11 realistic product entries
- Includes: Product Name, MOQ, Lead Time, Description, Price Range
- Product categories: Water bottles, kitchen items, electronics, fitness, promotional items

**Test Scenarios:**
- Query: "Do you have water bottles?" → Should retrieve Stainless Steel Water Bottle
- Query: "What products have 500 unit MOQ?" → Should retrieve multiple matching products
- Query: "Show me products under $10" → Should retrieve products in that price range
- Query: "What is the lead time for yoga mats?" → Should retrieve specific product info

**Expected Behavior:**
- Product descriptions should be chunked appropriately
- Price ranges should be preserved in context
- MOQ and lead time should be retrievable

---

### 3. Reply_Templates_Test.csv
**Purpose:** Test template retrieval for common scenarios

**Content:**
- 8 professional reply templates
- Scenarios: Shipping Delay, Out of Stock, Payment Confirmation, Quotation Follow-up, Sample Approval, Holiday Notice, Quality Issue Response, Price Negotiation

**Test Scenarios:**
- Query: "Customer's order is delayed" → Should retrieve Shipping Delay template
- Query: "Product is out of stock" → Should retrieve Out of Stock template
- Query: "Customer wants to negotiate price" → Should retrieve Price Negotiation template
- Query: "Quality complaint from customer" → Should retrieve Quality Issue Response template

**Expected Behavior:**
- Templates should be retrieved as complete units (no mid-template chunking)
- Placeholders like [Customer Name] should be preserved
- Semantic matching should work (e.g., "delayed shipment" matches "Shipping Delay")

---

### 4. Long_FAQ_Test.md
**Purpose:** Test chunking, overlap, and long-document retrieval

**Content:**
- ~3000 words comprehensive FAQ document
- 8 major sections with subsections
- Tables, lists, and structured content
- Realistic foreign trade company handbook

**Test Scenarios:**
- Query: "What are your business hours?" → Should retrieve General Business Information section
- Query: "How does the ordering process work?" → Should retrieve Ordering Process section
- Query: "What Incoterms do you support?" → Should retrieve Shipping and Logistics section
- Query: "What certifications do you have?" → Should retrieve Quality Control section

**Expected Behavior:**
- Document should be chunked into ~800 character segments
- Overlap (120 chars) should prevent information loss at chunk boundaries
- Headings should be preserved in chunks for context
- Tables should remain readable after chunking
- Multi-paragraph sections should be retrievable

**Chunking Quality Test:**
- Check that no sentence is cut mid-way
- Check that related information stays together
- Check that chunk boundaries don't break tables or lists

---

### 5. Corrupted_Test.txt
**Purpose:** Test error handling and parser robustness

**Content:**
- Intentionally malformed data
- Mixed encodings (English, Chinese, Spanish, French)
- Excessive whitespace
- Broken tables and lists
- Inconsistent line breaks
- Special characters and symbols
- Duplicate and contradictory information
- Embedded code snippets
- Very long single lines
- Null and empty values

**Test Scenarios:**
- Upload this file → Should not crash the system
- Parser should handle gracefully → Extract valid information where possible
- Error logs should be generated → But system continues functioning
- Retrieval should work → Even with imperfect data

**Expected Behavior:**
- No system crash or exception propagation
- Warning logs generated for parsing issues
- Valid information extracted despite formatting problems
- Retrieval returns best-effort results
- UI shows file processed with warnings

---

## Recommended Testing Workflow

### Phase 1: Individual File Upload
1. Upload `FAQ_Test.csv` → Verify 23 chunks indexed
2. Upload `Product_Catalog_Test.csv` → Verify 11 chunks indexed
3. Upload `Reply_Templates_Test.csv` → Verify 8 chunks indexed
4. Upload `Long_FAQ_Test.md` → Verify ~15-20 chunks indexed (depends on chunking)
5. Upload `Corrupted_Test.txt` → Verify graceful handling

### Phase 2: Retrieval Quality Test
For each test scenario listed above:
1. Enter customer query in CRM page
2. Click "Generate Draft Reply"
3. Check "KB Context: Yes ✓" indicator
4. Verify AI reply uses retrieved context appropriately
5. Check that reply is relevant and accurate

### Phase 3: Edge Cases
- **Empty KB:** Generate reply without any documents → Should work without KB context
- **Irrelevant Query:** Ask about something not in KB → AI should say "I don't have that information"
- **Ambiguous Query:** Ask vague question → AI should ask for clarification
- **Multi-topic Query:** Ask about MOQ and shipping together → Should retrieve both contexts

### Phase 4: Performance Test
- Upload all 5 files at once
- Check total chunk count (~60-70 chunks expected)
- Test retrieval speed (should be < 1 second for top_k=5)
- Test with multiple concurrent queries

---

## Expected Retrieval Behavior

### Good Retrieval (KB Context: Yes ✓)
- Customer asks: "What is your MOQ?"
- System retrieves: FAQ entry about MOQ
- AI reply: "Our MOQ depends on the product model. For standard items it is typically 500 units..."

### No Relevant Context (KB Context: No)
- Customer asks: "What is your company address?"
- System retrieves: No relevant chunks
- AI reply: "I don't have that information in our knowledge base. Please contact our sales team directly."

### Partial Context (KB Context: Yes ✓)
- Customer asks: "What is the MOQ and lead time for water bottles?"
- System retrieves: MOQ FAQ + Product Catalog entry for water bottle
- AI reply: Combines both pieces of information

---

## Validation Checklist

### Document Loading
- [ ] All 5 files upload successfully
- [ ] CSV files parsed correctly (columns preserved)
- [ ] Markdown file preserves formatting
- [ ] TXT file handles encoding issues gracefully
- [ ] No system crashes or unhandled exceptions

### Chunking Quality
- [ ] Chunks are ~800 characters
- [ ] Overlap is ~120 characters
- [ ] No mid-sentence cuts
- [ ] Tables remain readable
- [ ] Lists stay together

### Embedding Quality
- [ ] Local embeddings work (sentence-transformers)
- [ ] OpenAI embeddings work (if API key provided)
- [ ] OpenAI-Compatible embeddings work (if configured)
- [ ] Embedding time is reasonable (< 5 seconds per file)

### Retrieval Quality
- [ ] Semantic search works (not just keyword matching)
- [ ] Top_k=5 returns relevant results
- [ ] Irrelevant queries return empty or low-confidence results
- [ ] Multi-topic queries retrieve multiple relevant chunks

### CRM Integration
- [ ] "KB Context: Yes ✓" shows when context is used
- [ ] "KB Context: No" shows when no context found
- [ ] AI replies incorporate retrieved context naturally
- [ ] AI doesn't hallucinate information not in KB
- [ ] AI asks for clarification when information is incomplete

### Error Handling
- [ ] Corrupted file doesn't crash system
- [ ] Parser errors are logged but don't stop processing
- [ ] Invalid file types are rejected gracefully
- [ ] Large files (>20MB) show appropriate warning in demo mode
- [ ] Empty files are handled without errors

---

## Known Limitations (Demo Mode)

1. **File Size:** Demo mode recommends files under 20MB. Large files should be handled in production with background processing.

2. **Embedding Provider:** Default is local (sentence-transformers). OpenAI embeddings require API key configuration.

3. **Vector DB:** Uses ChromaDB with local persistence. Production should consider Qdrant for better performance.

4. **Multi-tenancy:** Current demo uses single collection. Production needs tenant_id isolation.

5. **Document Management:** No UI for viewing/deleting individual documents yet (coming in Phase 0.4E).

---

## Next Steps

After validating with this test dataset:

1. **Phase 0.4E:** Add document list UI with delete functionality
2. **Phase 0.5:** Add embedding provider selection in AI Settings
3. **Phase 0.6:** Implement multi-tenant collection isolation
4. **Production:** Migrate to Qdrant for better vector search performance

---

## Contact

For questions or issues with test data:
- Check `buildway-ai-core/docs/ROADMAP.md` for development status
- Review `buildway-ai-core/core/rag/` for implementation details
- Test with `apps/streamlit_demo/app.py` Knowledge Base page

---

*Last Updated: May 2026*
