# agents/technical/debugger_agent.py
from typing import Any
from agents.base.base_agent import BaseAgent, AgentConfig
from core.graph_engine.state import NeuralState
from core.self_healing.engine import SelfHealingEngine


class DebuggerAgent(BaseAgent):
    """
    Advanced Debugger Agent.
    Uses SelfHealingEngine to classify errors and generate repair strategies.
    """

    def __init__(self):
        config = AgentConfig(
            name="DebuggerAgent",
            role="Senior Debugger & Code Fixer",
            goal="Analyze error logs, understand root causes, and apply fixes.",
            backstory=(
                "You are an expert debugger. You don't just guess; you analyze stack traces, "
                "identify the exact line of failure, and provide surgical code fixes."
            ),
            constraints=[
                "Return ONLY the fixed code block",
                "Do not explain unless necessary",
                "Maintain existing code structure"
            ],
            examples=["Fix syntax errors", "Resolve import errors", "Fix logic bugs"]
        )
        super().__init__(config)
        # Sprint 3'te oluşturduğumuz motoru yüklüyoruz
        self.engine = SelfHealingEngine()

    async def _build_user_prompt(self, state: NeuralState) -> str:
        """
        Durumu analiz eder:
        1. Test sonuçlarına bakar.
        2. Hata varsa SelfHealingEngine'den teşhis ve prompt ister.
        """

        # 1. Test Sonuçlarını Kontrol Et
        test_res = state.artifacts.get("test_results", {})

        # Eğer testler başarılıysa veya hiç test yoksa
        if test_res.get("success", False):
            self.logger.info("✅ Tests passed. No debugging needed.")
            return "NO_OP: Tests passed. No action required."

        # 2. Hatayı ve Kodu Al
        error_msg = test_res.get("output", "Unknown Error")

        code_map = state.artifacts.get("generated_code", {})
        if not code_map:
            return "NO_OP: No code found to debug."

        # İlk dosyayı al (MVP için)
        filename, code = list(code_map.items())[0]

        # 3. Motoru Kullanarak Teşhis Koy (Diagnosis)
        # Bu, hatanın türünü (Syntax, Logic, Import) belirler
        diagnosis = self.engine.diagnose(error_msg, code)

        self.logger.info(
            f"🚑 Diagnosis: {diagnosis.type.value}",
            extra={"file": filename, "details": diagnosis.details}
        )

        # 4. Motorun ürettiği "Akıllı Prompt"u döndür
        # Örn: "Fix Syntax Error in line 5..."
        return diagnosis.fix_prompt

    async def _process_response(self, response: Any, state: NeuralState) -> str:
        """
        LLM'den gelen düzeltilmiş kodu işler ve State'i günceller.
        """
        content = getattr(response, "content", str(response))

        # Eğer işlem yapılmasına gerek yoksa çık
        if "NO_OP" in content:
            return content

        # 1. Markdown Temizliği (Kod Bloğunu Ayıkla)
        fixed_code = content
        if "```" in content:
            parts = content.split("```")
            # Genelde: [0] text, [1] code, [2] text
            if len(parts) >= 2:
                # python/javascript gibi dil etiketlerini temizle
                fixed_code = parts[1].replace("python", "").replace("javascript", "").strip()

        # 2. Patch Uygulama (State Artifact Güncelleme)
        code_map = state.artifacts.get("generated_code", {})
        if code_map:
            filename = list(code_map.keys())[0]

            # Yeni artifact sözlüğü oluştur (Immutable prensibi için kopya)
            new_artifacts = state.artifacts.copy()

            # Kodu güncelle
            new_artifacts["generated_code"] = {filename: fixed_code}

            # Test sonuçlarını SİL (Ki pipeline döngüsünde tekrar test edilsin)
            if "test_results" in new_artifacts:
                del new_artifacts["test_results"]

            # State'i güncelle
            state.artifacts = new_artifacts

            return f"Applied fix to '{filename}'. Ready for re-test.\nPreview: {fixed_code[:50]}..."

        return "Could not apply fix: No source file found."