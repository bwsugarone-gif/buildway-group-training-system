# -*- coding: utf-8 -*-
"""
core/agents/agent_router.py
Buildway AI Core — Generic Agent Routing Framework

This module provides the routing infrastructure only.
Agent definitions (domain-specific agents) must be provided by each vertical.

Usage:
    from core.agents.agent_router import AgentRouter

    router = AgentRouter(agent_definitions=MY_AGENTS)
    selected = router.select_agents(["agent_a", "agent_b"])
    prompt = router.build_prompt(selected, context="...")
"""

from pathlib import Path
from typing import Any


class AgentRouter:
    """
    Generic agent router. Accepts agent definitions from the calling vertical.
    Does not contain any domain-specific agent logic.
    """

    def __init__(
        self,
        agent_definitions: dict[str, dict],
        instruction_dir: Path | None = None,
    ):
        """
        Args:
            agent_definitions: Dict of agent_id -> agent config dict.
                Each config should have keys: id, name, desc, focus, report_section,
                instruction_files (optional), fallback_instruction.
            instruction_dir: Optional directory to load .md instruction files from.
        """
        self.agents = agent_definitions
        self.instruction_dir = instruction_dir

    def list_agents(self) -> list[dict]:
        """Return all agent definitions as a list."""
        return list(self.agents.values())

    def get_agent(self, agent_id: str) -> dict | None:
        """Get a single agent definition by ID."""
        return self.agents.get(agent_id)

    def select_agents(self, agent_ids: list[str]) -> list[dict]:
        """Return agent definitions for the given IDs (skips unknown IDs)."""
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def load_instruction(self, agent: dict) -> str:
        """
        Load agent instruction from file or fallback to inline instruction.
        Tries each filename in agent['instruction_files'] in order.
        """
        if self.instruction_dir:
            for fname in agent.get("instruction_files", []):
                fpath = self.instruction_dir / fname
                if fpath.exists():
                    try:
                        return fpath.read_text(encoding="utf-8").strip()
                    except Exception:
                        pass
        return agent.get("fallback_instruction", f"Analyse the document as {agent.get('name', 'an agent')}.")

    def build_prompt(
        self,
        selected_agents: list[dict],
        context: str,
        question: str = "",
        extra_instructions: str = "",
    ) -> str:
        """
        Build a combined analysis prompt for the selected agents.

        Args:
            selected_agents: List of agent dicts (from select_agents).
            context: Document text / evidence to analyse.
            question: Optional user question.
            extra_instructions: Any additional instructions to append.

        Returns:
            A formatted prompt string ready for LLM submission.
        """
        agent_blocks = []
        for agent in selected_agents:
            instruction = self.load_instruction(agent)
            focus_list = "\n".join(f"  - {f}" for f in agent.get("focus", []))
            block = (
                f"## {agent.get('name', agent['id'])}\n"
                f"Focus areas:\n{focus_list}\n\n"
                f"Instructions:\n{instruction}"
            )
            agent_blocks.append(block)

        agents_section = "\n\n---\n\n".join(agent_blocks)

        prompt_parts = [
            "You are a multi-agent AI analysis system.",
            "",
            "## Active Agents",
            agents_section,
            "",
            "## Document / Evidence",
            context.strip() if context else "(No document provided)",
        ]

        if question:
            prompt_parts += ["", "## User Question", question.strip()]

        if extra_instructions:
            prompt_parts += ["", "## Additional Instructions", extra_instructions.strip()]

        prompt_parts += [
            "",
            "## Output Requirements",
            "- Provide structured analysis for each active agent.",
            "- Cite specific evidence from the document.",
            "- Flag any conflicts or gaps in the evidence.",
            "- Be concise and actionable.",
        ]

        return "\n".join(prompt_parts)

    def get_report_sections(self, selected_agents: list[dict]) -> list[str]:
        """Return the report section names for the selected agents."""
        return [a.get("report_section", a.get("name", a["id"])) for a in selected_agents]
