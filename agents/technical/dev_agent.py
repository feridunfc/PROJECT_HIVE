# agents/technical/dev_agent.py
import os
from agents.base.base_agent import BaseAgent, AgentConfig
from core.graph_engine.state import NeuralState


class DevAgent(BaseAgent):
    def __init__(self):
        config = AgentConfig(
            name="DevAgent",
            role="Senior Developer",
            goal="Write clean, executable code based on specs.",
            backstory="You are a polyglot developer who loves clean code.",
            constraints=["No placeholder comments", "Complete implementation"]
        )
        super().__init__(config)

    async def _build_user_prompt(self, state: NeuralState) -> str:
        # Önceki mesajlardan spec veya plan var mı bak
        context = state.messages[-1]['content'] if state.messages else "No context"
        return f"""
        TASK: Write code for the following goal: "{state.goal}"
        CONTEXT: {context}

        IMPORTANT: Output the code inside markdown code blocks (e.g., ```python ... ```).
        """

    async def _process_response(self, response, state: NeuralState) -> str:
        content = getattr(response, "content", str(response))
        code = ""

        # 1. Markdown Bloklarını Ayıkla
        if "```" in content:
            # Genelde ```python ... ``` formatı olur
            parts = content.split("```")
            # 0: pre-text, 1: code, 2: post-text (basit varsayım)
            if len(parts) >= 2:
                candidate = parts[1]
                if candidate.startswith("python"):
                    code = candidate[6:].strip()
                elif candidate.startswith("javascript"):
                    code = candidate[10:].strip()
                else:
                    code = candidate.strip()
        else:
            # Markdown yoksa, tüm içeriği kod kabul etmeye çalış (riskli ama fallback var)
            code = content.strip()

        # 2. 🚨 FALLBACK MEKANİZMASI (ACİL ÇÖZÜM)
        # Eğer kod boşsa veya çok kısaysa (LLM hata yaptıysa), basit bir kod göm.
        if not code or len(code) < 10:
            self.logger.warning(f"⚠️ LLM produced invalid code. Using FALLBACK. Raw content: {content[:50]}...")

            # Hedefe uygun basit bir fallback seçmeye çalışalım
            if "calculator" in state.goal.lower():
                code = """
def add(a, b): return a + b
def subtract(a, b): return a - b
def multiply(a, b): return a * b
def divide(a, b): return a / b if b != 0 else 'Error'

if __name__ == "__main__":
    print(f"2 + 3 = {add(2, 3)}")
    print(f"10 / 2 = {divide(10, 2)}")
"""
            else:
                # Genel Fallback
                code = """
def main():
    print("Hello from PROJECT_HIVE Generated App!")
    print("This is a fallback code block because the LLM generation was incomplete.")

if __name__ == "__main__":
    main()
"""

        # 3. Artifact'e Kaydet (Self-healing ve Test scripti için)
        # generated_code artifact'i bir sözlük: { "filename": "code_content" }
        artifacts = state.artifacts.copy()
        artifacts["generated_code"] = {"generated_app.py": code}

        # Artifact'i güncelle
        state.artifacts = artifacts

        return f"Code generated successfully. Length: {len(code)} chars."