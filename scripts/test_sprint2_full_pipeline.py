import asyncio
import sys
import os
import json

# Proje kök dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph_engine.state import NeuralState
from agents.cognitive.supervisor_agent import SupervisorAgent
from agents.cognitive.architect_agent import ArchitectAgent
from agents.technical.dev_agent import DevAgent
from agents.technical.tester_agent import TesterAgent


async def main():
    print("🚀 STARTING FULL PIPELINE TEST (With Fallback)")
    print("============================================")

    # 1. State Başlat
    state = NeuralState(goal="Build a simple python calculator")

    # 2. Agentları Hazırla
    # (Not: Artık AgentConfig tabanlı oldukları için init parametreleri boş olabilir, default config çalışır)
    agents = [
        SupervisorAgent(),
        ArchitectAgent(),
        DevAgent(),
        TesterAgent()
    ]

    # 3. Pipeline Döngüsü
    for agent in agents:
        print(f"\n▶️  RUNNING: {agent.config.name}")
        try:
            state = await agent.execute(state)
            # Son mesajı göster
            if state.messages:
                print(f"   🗣️  Output: {state.messages[-1]['content'][:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n=====================")
    print("🏁 PIPELINE FINISHED")

    # 4. Dosyaya Yazma ve Kontrol (Senin bahsettiğin kısım)
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    generated_code = state.artifacts.get("generated_code", {})

    if generated_code:
        # Artifact'ten alıp dosyaya yaz
        filename, content = list(generated_code.items())[0]
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"\n💾 Saved code to: {filepath}")

        # 5. Compile/Syntax Check
        print('\n=== GENERATED CODE CHECK ===')
        print(content)
        print('============================')
        try:
            compile(content, filepath, 'exec')
            print('✅ Code compiles successfully!')
        except SyntaxError as e:
            print(f'❌ Syntax error: {e}')
    else:
        print("❌ No generated code found in artifacts.")

    # State Dump (Opsiyonel debug)
    # print(json.dumps(state.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())