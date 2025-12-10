from __future__ import annotations

from pathlib import Path

from agents.base.base_agent import AgentConfig, BaseAgent
from core.graph_engine.state import NeuralState
from core.self_healing.engine import SelfHealingEngine
from core.utils.logger import get_logger

logger = get_logger("DebuggerAgent")


class DebuggerAgent(BaseAgent):
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.healer = SelfHealingEngine()
        config = AgentConfig(
            name="Debugger",
            role="debugging specialist",
            goal="Diagnose errors and propose code fixes.",
        )
        super().__init__(config)

    async def _build_user_prompt(self, state: NeuralState) -> str:
        code_path_str = state.artifacts.get("generated_code_path", "")
        last_error = state.errors[-1]["message"] if state.errors else ""
        code = ""
        if code_path_str:
            path = Path(code_path_str)
            if path.exists():
                code = path.read_text(encoding="utf-8")

        return f"""Overall goal: {state.goal}

Last error:
{last_error}

Current code:
{code}

Propose a fixed version of the file. 
Return ONLY the Python code."""

    async def _process_response(self, response, state: NeuralState) -> str:
        code_path_str = state.artifacts.get("generated_code_path", "")
        if not code_path_str:
            return "No code path to patch."

        path = Path(code_path_str)
        fixed_code = response.content.strip()
        path.write_text(fixed_code, encoding="utf-8")
        logger.info("Patched code written", extra={"run_id": state.run_id, "path": code_path_str})
        state.artifacts["debugged"] = True
        return f"Patched code at {code_path_str}"
