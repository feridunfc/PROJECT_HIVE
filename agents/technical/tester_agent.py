from __future__ import annotations

import subprocess
from pathlib import Path

from agents.base.base_agent import AgentConfig, BaseAgent
from core.graph_engine.state import NeuralState
from core.utils.logger import get_logger

logger = get_logger("TesterAgent")


class TesterAgent(BaseAgent):
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        config = AgentConfig(
            name="Tester",
            role="qa engineer",
            goal="Validate that the generated code at least compiles.",
        )
        super().__init__(config)

    async def _build_user_prompt(self, state: NeuralState) -> str:
        # Bu agent LLM kullanmak zorunda değil aslında; ama interface'i tutarlı kalsın diye boş prompt döndürüyoruz.
        return "No-op."

    # agents/technical/tester_agent.py (güncelle)

    # agents/technical/tester_agent.py (sadece ilgili kısım)

    async def _process_response(self, response, state: NeuralState) -> str:
        # ... önceki kod ...

        # Syntax kontrolü
        try:
            with open(code_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            # compile the code to check syntax
            compile(code_content, code_path, 'exec')
            self.logger.info("Syntax check passed")
        except SyntaxError as e:
            self.logger.error(f"Syntax check failed: {e}")
            state.add_artifact(
                key="test_result",
                value="fail",
                artifact_type="test_result",
                metadata={"error": f"Syntax error: {e}"}
            )
            return f"Syntax error: {e}"
        except Exception as e:
            self.logger.error(f"Failed to read/compile code: {e}")
            state.add_artifact(
                key="test_result",
                value="fail",
                artifact_type="test_result",
                metadata={"error": str(e)}
            )
            return f"Failed to test code: {e}"

        # ... diğer testler ...

    async def execute(self, state: NeuralState) -> NeuralState:
        # BaseAgent.execute yerine gerçek test mantığı
        code_path_str = state.artifacts.get("generated_code_path")
        if not code_path_str:
            logger.warning("No generated_code_path in state", extra={"run_id": state.run_id})
            state.artifacts["test_result"] = "missing"
            return state

        code_path = Path(code_path_str)
        if not code_path.exists():
            logger.error("Generated file missing", extra={"run_id": state.run_id, "path": code_path_str})
            state.artifacts["test_result"] = "missing"
            return state

        try:
            subprocess.check_call(
                ["python", "-m", "py_compile", str(code_path)],
                cwd=self.project_root,
            )
            state.artifacts["test_result"] = "ok"
            logger.info("Syntax check passed", extra={"run_id": state.run_id})
        except subprocess.CalledProcessError as exc:
            msg = f"Syntax check failed: {exc}"
            state.artifacts["test_result"] = "fail"
            state.add_error("syntax_error", msg, {"path": code_path_str})
            logger.error("Syntax check failed", extra={"run_id": state.run_id, "error": str(exc)})
        return state
