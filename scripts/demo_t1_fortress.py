import asyncio
import sys
import os

# Proje kök dizinini path'e ekle (Modüllerin bulunabilmesi için)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipelines.t1_fortress_pipeline import T1FortressPipeline
from core.utils.logger import get_logger

logger = get_logger("DemoRunner")


async def main():
    print("\n🏰 STARTING PROJECT_HIVE T1 FORTRESS RUN")
    print("=========================================")

    # 1. Pipeline'ı Başlat (Policy, Budget, Swarm, Agents yüklenir)
    try:
        pipeline = T1FortressPipeline()
    except TypeError as e:
        print(f"❌ Initialization Error: {e}")
        return

    # 2. Görev Tanımla
    # Hem kod yazdıracak hem de test ettirecek bir görev verelim.
    goal = "Create a Python script that calculates Fibonacci numbers recursively."

    logger.info(f"🎯 Goal: {goal}")

    # 3. Çalıştır
    try:
        final_state = await pipeline.run(goal)
    except Exception as e:
        print(f"❌ Execution Error: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Rapor
    print("\n🏁 EXECUTION FINISHED")
    print("=====================")

    # Bütçe
    print(f"💰 Cost: ${final_state.budget_used:.6f}")

    # Hatalar ve Policy İhlalleri
    if final_state.errors:
        print(f"🐞 Errors ({len(final_state.errors)}):")
        for err in final_state.errors:
            print(f"   - [{err.get('type')}] {err.get('message')}")
    else:
        print("✅ No errors logged.")

    # Artifacts (Üretilen Kod)
    print(f"📦 Artifacts: {list(final_state.artifacts.keys())}")

    if "generated_code" in final_state.artifacts:
        print("\n📜 Generated Code Preview:")
        code_map = final_state.artifacts["generated_code"]
        if isinstance(code_map, dict) and code_map:
            filename = list(code_map.keys())[0]
            print(f"--- {filename} ---")
            print(code_map[filename])
            print("-------------------")


if __name__ == "__main__":
    asyncio.run(main())