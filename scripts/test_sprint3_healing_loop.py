import asyncio
from pipelines.t0_velocity_pipeline import T0VelocityPipeline

async def main():
    print("🚀 Running T0 Pipeline with Enterprise Skills & Healing")
    pipeline = T0VelocityPipeline()
    result = await pipeline.run("Build a simple Python calculator with a purposeful bug")

    print("\n🏁 Final Artifacts:")
    print(result.artifacts.keys())

if __name__ == "__main__":
    asyncio.run(main())
