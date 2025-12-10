# PROJECT_HIVE – Enterprise Core (Sprint 0–3)

Bu repo, PROJECT_HIVE / Neural Hive mimarisinin **Enterprise-ready Sprint 0–3 çekirdeğini**
içerir. Hedef:

- ✅ Sprint 0 – Config & Logging (production temeli)
- ✅ Sprint 1 – Enterprise LLM Router & Gelişmiş Graph Engine
- ✅ Sprint 2 – Enterprise Agent Framework (telemetry, budget, PII)
- ✅ Sprint 3 – Swarm & Self-Healing iskeleti

> Not: Bu repo **iskelettir**. Gerçek production ortamında:
> - Secret yönetimi (Vault vs.)
> - Gelişmiş observability (OpenTelemetry, AgentOps)
> - CI/CD & infra (Docker/Kubernetes)
> harici olarak eklenmelidir.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Örnek Çalıştırma

```bash
# Basit graph demo
python -m scripts.demo_graph

# Sprint 1 – LLM router demo
python -m scripts.demo_llm_router

# Sprint 2 – Agent pipeline demo
python -m scripts.demo_t0_pipeline

# Sprint 3 – Swarm & Self-healing demo
python -m scripts.demo_swarm_self_healing
```

Ortam değişkenleri için `.env.example` dosyasına bakın.
