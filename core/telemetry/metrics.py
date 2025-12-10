from __future__ import annotations
try:
    from prometheus_client import Counter, Histogram
    AGENT_EXECUTIONS = Counter("agent_executions_total", "Total executions", ["agent"])
    LLM_LATENCY = Histogram("llm_latency_seconds", "LLM latency", ["provider"])
except ImportError:
    AGENT_EXECUTIONS = None
    LLM_LATENCY = None

def track_agent_execution(agent_name: str) -> None:
    if AGENT_EXECUTIONS:
        AGENT_EXECUTIONS.labels(agent=agent_name).inc()

def observe_llm_latency(provider: str, latency: float) -> None:
    if LLM_LATENCY:
        LLM_LATENCY.labels(provider=provider).observe(latency)
