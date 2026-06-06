# -*- coding: utf-8 -*-
"""
verticals/construction/agents.py
Buildway AI Core — Construction Vertical Agent Definitions

All construction-specific agents (Safety, PM, QS, Engineering, etc.)
are defined here. These are passed to core.agents.agent_router.AgentRouter.

DO NOT place these definitions in core/. They are construction-specific.
"""

CONSTRUCTION_AGENTS: dict[str, dict] = {
    "accounting": {
        "id": "accounting",
        "name": "Accounting Agent",
        "icon": "AC",
        "desc": "檢視付款、發票、成本記錄、工資及會計風險。",
        "focus": ["付款及發票", "工資及成本記錄", "會計合規", "財務風險"],
        "report_section": "Accounting Agent 分析",
        "instruction_files": ["agents-accounting-agent.md"],
        "fallback_instruction": "從會計、付款、發票、成本記錄及財務控制角度分析事項，指出金額、責任、證據及跟進建議。",
    },
    "drafting": {
        "id": "drafting",
        "name": "Drafting Agent",
        "icon": "DR",
        "desc": "檢視圖則、版本、標註、RFI 及設計文件一致性。",
        "focus": ["圖則版本", "設計文件", "RFI", "圖則不一致"],
        "report_section": "Drafting Agent 分析",
        "instruction_files": ["agents-drafting-agent.md"],
        "fallback_instruction": "從圖則、設計文件、版本控制、標註及 RFI 角度分析，指出圖則差異及需澄清事項。",
    },
    "engineering": {
        "id": "engineering",
        "name": "Engineering Agent",
        "icon": "EN",
        "desc": "分析施工方法、進度、技術風險、工序及工程影響。",
        "focus": ["施工方法", "工程進度", "技術風險", "工序協調"],
        "report_section": "Engineering Agent 分析",
        "instruction_files": ["agents-engineering-agent.md"],
        "fallback_instruction": "從工程技術、施工方法、進度及技術風險角度分析，指出工程問題及建議解決方案。",
    },
    "foreman": {
        "id": "foreman",
        "name": "Foreman Agent",
        "icon": "FM",
        "desc": "分析工地日常運作、工人管理、工序安排及現場問題。",
        "focus": ["工地日常運作", "工人管理", "工序安排", "現場問題"],
        "report_section": "Foreman Agent 分析",
        "instruction_files": ["agents-foreman-agent.md"],
        "fallback_instruction": "從工地管理、工人協調、工序安排及現場執行角度分析，指出實際操作問題及改善建議。",
    },
    "material": {
        "id": "material",
        "name": "Material Agent",
        "icon": "MT",
        "desc": "檢視物料供應、質量、存倉及物料相關風險。",
        "focus": ["物料供應", "物料質量", "存倉管理", "物料風險"],
        "report_section": "Material Agent 分析",
        "instruction_files": ["agents-material-agent.md"],
        "fallback_instruction": "從物料供應、質量控制、存倉及物料管理角度分析，指出物料問題及採購建議。",
    },
    "pm": {
        "id": "pm",
        "name": "PM Agent",
        "icon": "PM",
        "desc": "分析項目管理、進度、風險、合約及整體協調。",
        "focus": ["項目進度", "風險管理", "合約管理", "整體協調"],
        "report_section": "PM Agent 分析",
        "instruction_files": ["agents-pm-agent.md"],
        "fallback_instruction": "從項目管理角度分析，評估進度、風險、合約執行及整體協調，提出管理建議。",
    },
    "qs": {
        "id": "qs",
        "name": "QS Agent",
        "icon": "QS",
        "desc": "分析工程量、估算、變更令、索償及成本控制。",
        "focus": ["工程量計算", "成本估算", "變更令", "索償"],
        "report_section": "QS Agent 分析",
        "instruction_files": ["agents-qs-agent.md"],
        "fallback_instruction": "從工料測量角度分析，評估工程量、成本、變更令及索償，提出量度及財務建議。",
    },
    "safety": {
        "id": "safety",
        "name": "Safety Agent",
        "icon": "SF",
        "desc": "識別安全隱患、違規、事故風險及安全合規問題。",
        "focus": ["安全隱患", "安全合規", "事故風險", "安全措施"],
        "report_section": "Safety Agent 分析",
        "instruction_files": ["agents-safety-agent.md"],
        "fallback_instruction": "從工地安全角度分析，識別安全隱患、違規事項及事故風險，提出安全改善建議。",
    },
    "surveying": {
        "id": "surveying",
        "name": "Surveying Agent",
        "icon": "SV",
        "desc": "分析測量數據、界線、高程及測量相關問題。",
        "focus": ["測量數據", "界線問題", "高程控制", "測量合規"],
        "report_section": "Surveying Agent 分析",
        "instruction_files": ["agents-surveying-agent.md"],
        "fallback_instruction": "從測量角度分析，評估測量數據、界線、高程及測量合規，提出測量建議。",
    },
}


def get_agent_router(instruction_dir=None):
    """
    Convenience factory: returns an AgentRouter configured for construction.

    Args:
        instruction_dir: Optional Path to directory containing .md instruction files.

    Returns:
        core.agents.agent_router.AgentRouter instance.
    """
    from core.agents.agent_router import AgentRouter
    return AgentRouter(
        agent_definitions=CONSTRUCTION_AGENTS,
        instruction_dir=instruction_dir,
    )
