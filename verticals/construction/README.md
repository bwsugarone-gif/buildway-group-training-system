# Construction Vertical

This vertical contains all construction-specific logic for the Buildway AI Core.

## What belongs here

- Agent definitions (Safety, PM, QS, Engineering, Foreman, Material, Drafting, Surveying, Accounting)
- Site-specific engines (site context, site logic, site instructions)
- Risk classification for construction (risk matrix, risk calibrator)
- Resource and workforce management
- Delay and concern analysis
- HK regulations references

## What does NOT belong here

All generic logic (memory, RAG, OCR, document processing, report generation, action tracking)
lives in `core/`. This vertical only contains construction-specific extensions.

## Agent List

| Agent | ID | Description |
|---|---|---|
| Safety Agent | safety | 安全隱患、違規、事故風險 |
| PM Agent | pm | 項目管理、進度、風險、合約 |
| QS Agent | qs | 工程量、估算、變更令、索償 |
| Engineering Agent | engineering | 施工方法、進度、技術風險 |
| Foreman Agent | foreman | 工地日常運作、工人管理 |
| Material Agent | material | 物料供應、質量、存倉 |
| Drafting Agent | drafting | 圖則、版本、RFI |
| Surveying Agent | surveying | 測量數據、界線、高程 |
| Accounting Agent | accounting | 付款、發票、成本記錄 |

## Usage

```python
from verticals.construction.agents import get_agent_router

router = get_agent_router(instruction_dir=Path("agents/"))
selected = router.select_agents(["safety", "pm", "engineering"])
prompt = router.build_prompt(selected, context=document_text)
```

## Source

Extracted from HK-AICOS (https://github.com/bwsugarone-gif/hk-aicos)
