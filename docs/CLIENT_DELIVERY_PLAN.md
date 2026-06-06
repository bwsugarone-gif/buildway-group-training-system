# Client Delivery Plan

## Buildway AI Core v0.1.0

### What is delivered

This release delivers the **architecture foundation** of Buildway AI Core:

1. **Core modules** — 9 generic AI infrastructure modules extracted from HK-AICOS
2. **Construction vertical** — Full agent definitions (9 agents) ready for use
3. **CRM vertical** — Initial placeholder with 4 modules
4. **Document AI vertical** — Placeholder
5. **Streamlit demo app** — Working demo of core modules
6. **Documentation** — Architecture, roadmap, known limitations

### What is NOT in this release

- Production API server
- Authentication / security layer
- Vector embeddings / semantic search
- CRM full implementation
- Document AI implementation

### Deployment

**Local / Development:**
```bash
pip install -r requirements.txt
cd apps/streamlit_demo
streamlit run app.py
```

**Streamlit Cloud:**
- Point to `apps/streamlit_demo/app.py`
- Set environment variables in Streamlit Cloud secrets

### Environment Variables

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

### Integration with HK-AICOS

The construction vertical (`verticals/construction/`) is designed to be a drop-in
replacement for the agent definitions in HK-AICOS. To migrate:

1. Replace `streamlit-app/utils/agent_router.py` AGENT_DEFINITIONS with
   `from verticals.construction.agents import CONSTRUCTION_AGENTS`
2. Replace direct calls to session_memory with `core.memory.session_memory`
3. Replace direct calls to rag_manager with `core.rag.rag_manager`

### Next Steps

1. Review architecture and provide feedback
2. Confirm CRM vertical requirements
3. Plan Phase 2 (API server + security)
