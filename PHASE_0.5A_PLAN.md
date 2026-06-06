# Phase 0.5A Implementation Plan — KB Document Management

## Status: IN PROGRESS

### Completed ✓
1. vector_store.py
   - get_all_documents()
   - get_documents_by_filename()

2. retriever.py
   - list_documents()
   - re_index_document()

### Remaining Tasks

#### 1. Update app.py KB Section (Lines 815-850)
Replace placeholder with:
```python
# List documents
documents = st.session_state["rag_retriever"].list_documents()

if not documents:
    st.info("No documents indexed yet.")
else:
    for doc in documents:
        col1, col2, col3, col4, col5 = st.columns([3, 1, 2, 1, 1])
        with col1:
            st.write(f"📄 **{doc['file_name']}**")
        with col2:
            st.write(f"{doc['chunk_count']} chunks")
        with col3:
            st.write(doc['indexed_at'][:19] if doc['indexed_at'] else "")
        with col4:
            if st.button("🗑️", key=f"del_{doc['file_name']}"):
                deleted = st.session_state["rag_retriever"].delete_document(doc['file_name'])
                st.success(f"Deleted {deleted} chunks")
                st.rerun()
        with col5:
            if st.button("🔄", key=f"reindex_{doc['file_name']}"):
                st.warning("Re-index requires original file")
```

#### 2. Add KB Search Test Box (After document list)
```python
st.divider()
st.subheader("Search Knowledge Base")

search_col1, search_col2 = st.columns([4, 1])
with search_col1:
    search_query = st.text_input("Search query", placeholder="e.g., What is MOQ?")
with search_col2:
    top_k = st.number_input("Top K", min_value=1, max_value=10, value=5)

if st.button("Search KB"):
    if search_query:
        results = st.session_state["rag_retriever"].search(search_query, top_k=top_k)
        if results:
            for i, result in enumerate(results, 1):
                with st.expander(f"Result {i} — {result['metadata'].get('file_name', 'unknown')} (distance: {result['distance']:.4f})"):
                    st.write(result['text'][:500])
        else:
            st.info("No results found")
```

#### 3. Add CRM Retrieved Chunks Display (After Generate Reply)
In CRM section, after kb_context is retrieved:
```python
# Store retrieved results in session state
st.session_state["crm_last_kb_results"] = results if kb_used else []

# After draft reply display, add:
if st.session_state.get("crm_last_kb_results"):
    with st.expander("📚 Retrieved KB Context"):
        for i, result in enumerate(st.session_state["crm_last_kb_results"], 1):
            st.caption(f"**Source {i}:** {result['metadata'].get('file_name', 'unknown')}")
            st.write(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
            st.divider()
```

#### 4. Testing Checklist
- [ ] Upload FAQ_Test.csv
- [ ] Verify document appears in list
- [ ] Test delete button
- [ ] Test search box
- [ ] Test CRM with KB context display
- [ ] Test empty DB handling

#### 5. Commit
```bash
git add .
git commit -m "feat(rag): add knowledge base document management"
git push origin main
```

## Implementation Notes
- Keep existing UI style
- Use st.columns for layout
- Add error handling for all operations
- Preserve mobile compatibility (basic)
- Don't modify AI provider routing
- Don't modify CRM main workflow
