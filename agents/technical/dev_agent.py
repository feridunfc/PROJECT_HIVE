from __future__ import annotations

from pathlib import Path

from agents.base.base_agent import AgentConfig, BaseAgent
from core.graph_engine.state import NeuralState


class DevAgent(BaseAgent):
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        config = AgentConfig(
            name="Developer",
            role="software engineer",
            goal="Implement a minimal working version of the requested feature.",
            constraints=[
                "Code must run without syntax errors",
                "Prefer simplicity, avoid unnecessary abstractions",
            ],
        )
        super().__init__(config)

    async def _build_user_prompt(self, state: NeuralState) -> str:
        manifest = state.artifacts.get("manifest", "")
        return f"""Overall goal: {state.goal}

Architecture manifest:
{manifest}

Implement a SINGLE python file that provides a minimal working version.
Return ONLY the Python code for that file."""

    async def _process_response(self, response, state: NeuralState) -> str:
        code = response.content.strip()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / "generated_app.py"
        target.write_text(code, encoding="utf-8")
        state.artifacts["generated_code_path"] = str(target)
        return f"Generated code at {target}"
