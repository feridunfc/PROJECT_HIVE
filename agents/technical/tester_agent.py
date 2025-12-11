# agents/technical/tester_agent.py
from agents.base.base_agent import BaseAgent, AgentConfig
from core.graph_engine.state import NeuralState
from core.utils.logger import get_logger

logger = get_logger("TesterAgent")


class TesterAgent(BaseAgent):
    def __init__(self):
        # DÜZELTME: Parametresiz init. Config içeride tanımlanıyor.
        config = AgentConfig(
            name="TesterAgent",
            role="QA Engineer",
            goal="Validate code syntax and logic.",
            backstory="You are a meticulous tester. You check both syntax (compile) and logic (review).",
            constraints=["Check syntax errors", "Review logic flaws"]
        )
        super().__init__(config)

    async def _build_user_prompt(self, state: NeuralState) -> str:
        # Kodları Artifacts'ten al
        code_map = state.artifacts.get("generated_code", {})

        if not code_map:
            return "No code found to test."

        # Kodları prompt için hazırla
        context = ""
        for filename, code in code_map.items():
            context += f"\n--- FILE: {filename} ---\n```python\n{code}\n```\n"

        return f"""
        Review the following code for LOGICAL errors:
        {context}

        1. Does the code achieve the goal: "{state.goal}"?
        2. Are there any obvious bugs?
        3. Respond with "LOGIC PASS" if it looks good, or "LOGIC FAIL" with reasons.
        """

    async def _process_response(self, response, state: NeuralState) -> str:
        llm_content = getattr(response, "content", str(response))

        # 1. Deterministik Syntax Kontrolü (Python compile)
        syntax_passed = True
        syntax_errors = []

        code_map = state.artifacts.get("generated_code", {})
        for filename, code in code_map.items():
            try:
                # Kodu çalıştırmadan sadece derlemeyi dene (Syntax Check)
                compile(code, filename, 'exec')
                logger.info(f"✅ Syntax Check Passed: {filename}")
            except SyntaxError as e:
                syntax_passed = False
                msg = f"SyntaxError in {filename}: line {e.lineno}, {e.msg}"
                syntax_errors.append(msg)
                logger.error(msg)
                # State'e detaylı hata ekle (Debugger okusun diye)
                state.add_error("syntax_error", msg, {"filename": filename, "lineno": e.lineno})

        # 2. LLM Mantık Kontrolü
        logic_passed = "LOGIC PASS" in llm_content.upper() and "FAIL" not in llm_content.upper()

        # 3. Genel Başarı Durumu
        final_success = syntax_passed and logic_passed

        # Test Sonucunu Kaydet
        new_artifacts = state.artifacts.copy()
        new_artifacts["test_results"] = {
            "success": final_success,
            "output": f"Syntax: {'OK' if syntax_passed else 'FAIL'}. Logic: {'OK' if logic_passed else 'FAIL'}.\nDetails: {llm_content}\nSyntax Errors: {syntax_errors}"
        }
        state.artifacts = new_artifacts

        status_msg = "TESTS PASSED" if final_success else "TESTS FAILED"
        if not syntax_passed:
            status_msg += f" (Syntax Errors: {len(syntax_errors)})"

        return f"{status_msg}. {llm_content[:100]}..."