"""
Prometheus-compatible metrics collection for PROJECT_HIVE.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import time
import threading
from enum import Enum

try:
    from prometheus_client import Counter, Gauge, Histogram, Summary, REGISTRY

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️ Prometheus client not installed. Running in no-op mode.")


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricConfig:
    """Configuration for a metric."""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms
    quantiles: Optional[List[float]] = None  # For summaries


class EnterpriseMetrics:
    """
    Production-ready metrics collector with Prometheus support.
    """

    def __init__(self, prefix: str = "hive_"):
        self.prefix = prefix
        self.metrics: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._init_core_metrics()

    # -------------------------------
    # Backward compatible API (Sprint 3–4 support)
    # -------------------------------
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        """
        Backward compatible wrapper.
        Old code expects: metrics.increment_counter("x")
        New code expects: metrics._inc_counter("x", labels)
        """
        labels = labels or {"default": "true"}
        self._inc_counter(name, labels, increment=value)

    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        """
        Wrapper for histogram observations
        """
        labels = labels or {"default": "true"}
        self._observe_histogram(name, value, labels)

    def set_gauge_value(self, name: str, value: float, labels: Dict[str, str] = None):
        """
        Wrapper for gauge setter
        """
        labels = labels or {"default": "true"}
        self._set_gauge(name, value, labels)



    def _init_core_metrics(self):
        """Initialize core metrics for PROJECT_HIVE."""
        core_metrics = [
            # Agent Metrics
            MetricConfig(
                name="agent_executions_total",
                description="Total number of agent executions",
                metric_type=MetricType.COUNTER,
                labels=["agent_name", "status"]
            ),
            MetricConfig(
                name="agent_execution_duration_seconds",
                description="Duration of agent executions in seconds",
                metric_type=MetricType.HISTOGRAM,
                labels=["agent_name"],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
            ),
            MetricConfig(
                name="agent_tokens_used",
                description="Tokens used by agents",
                metric_type=MetricType.COUNTER,
                labels=["agent_name", "model"]
            ),

            # Pipeline Metrics
            MetricConfig(
                name="pipeline_runs_total",
                description="Total pipeline runs",
                metric_type=MetricType.COUNTER,
                labels=["pipeline_type", "status"]
            ),
            MetricConfig(
                name="pipeline_duration_seconds",
                description="Pipeline execution duration",
                metric_type=MetricType.HISTOGRAM,
                labels=["pipeline_type"],
                buckets=[10.0, 30.0, 60.0, 300.0, 600.0, 1800.0]
            ),

            # Self-Healing Metrics
            MetricConfig(
                name="self_healing_attempts_total",
                description="Total self-healing attempts",
                metric_type=MetricType.COUNTER,
                labels=["error_type", "success"]
            ),
            MetricConfig(
                name="self_healing_duration_seconds",
                description="Time spent on self-healing",
                metric_type=MetricType.HISTOGRAM,
                labels=["error_type"]
            ),

            # LLM Metrics
            MetricConfig(
                name="llm_calls_total",
                description="Total LLM API calls",
                metric_type=MetricType.COUNTER,
                labels=["provider", "model", "status"]
            ),
            MetricConfig(
                name="llm_call_duration_seconds",
                description="LLM API call duration",
                metric_type=MetricType.HISTOGRAM,
                labels=["provider", "model"]
            ),

            # Budget Metrics
            MetricConfig(
                name="budget_used_usd",
                description="Total budget used in USD",
                metric_type=MetricType.GAUGE,
                labels=["tenant_id"]
            ),
            MetricConfig(
                name="budget_remaining_usd",
                description="Remaining budget in USD",
                metric_type=MetricType.GAUGE,
                labels=["tenant_id"]
            ),

            # Queue/Performance Metrics
            MetricConfig(
                name="queue_size",
                description="Current queue size",
                metric_type=MetricType.GAUGE,
                labels=["queue_name"]
            ),
            MetricConfig(
                name="active_agents",
                description="Currently active agents",
                metric_type=MetricType.GAUGE
            ),
        ]

        for config in core_metrics:
            self._create_metric(config)

    def _create_metric(self, config: MetricConfig):
        """Create a metric based on configuration."""
        full_name = f"{self.prefix}{config.name}"

        if PROMETHEUS_AVAILABLE:
            if config.metric_type == MetricType.COUNTER:
                self.metrics[full_name] = Counter(
                    full_name, config.description, config.labels
                )
            elif config.metric_type == MetricType.GAUGE:
                self.metrics[full_name] = Gauge(
                    full_name, config.description, config.labels
                )
            elif config.metric_type == MetricType.HISTOGRAM:
                self.metrics[full_name] = Histogram(
                    full_name, config.description, config.labels,
                    buckets=config.buckets or Histogram.DEFAULT_BUCKETS
                )
            elif config.metric_type == MetricType.SUMMARY:
                self.metrics[full_name] = Summary(
                    full_name, config.description, config.labels,
                    quantiles=config.quantiles or [(0.5, 0.05), (0.9, 0.01), (0.99, 0.001)]
                )
        else:
            # Fallback to simple dictionary storage
            self.metrics[full_name] = {
                "type": config.metric_type,
                "description": config.description,
                "labels": config.labels,
                "values": {}
            }

    def record_agent_execution(self, agent_name: str, duration: float,
                               status: str = "success", tokens: int = 0,
                               model: str = "unknown"):
        """Record agent execution metrics."""
        with self._lock:
            # Increment execution counter
            self._inc_counter("agent_executions_total",
                              {"agent_name": agent_name, "status": status})

            # Record duration
            self._observe_histogram("agent_execution_duration_seconds",
                                    duration, {"agent_name": agent_name})

            # Record tokens if provided
            if tokens > 0:
                self._inc_counter("agent_tokens_used",
                                  {"agent_name": agent_name, "model": model},
                                  increment=tokens)

    def record_pipeline_run(self, pipeline_type: str, duration: float,
                            status: str = "completed"):
        """Record pipeline execution metrics."""
        with self._lock:
            self._inc_counter("pipeline_runs_total",
                              {"pipeline_type": pipeline_type, "status": status})
            self._observe_histogram("pipeline_duration_seconds",
                                    duration, {"pipeline_type": pipeline_type})

    def record_self_healing(self, error_type: str, duration: float,
                            success: bool):
        """Record self-healing metrics."""
        with self._lock:
            self._inc_counter("self_healing_attempts_total",
                              {"error_type": error_type, "success": str(success)})
            self._observe_histogram("self_healing_duration_seconds",
                                    duration, {"error_type": error_type})

    def record_llm_call(self, provider: str, model: str, duration: float,
                        status: str = "success", tokens_used: int = 0):
        """Record LLM API call metrics."""
        with self._lock:
            self._inc_counter("llm_calls_total",
                              {"provider": provider, "model": model, "status": status})
            self._observe_histogram("llm_call_duration_seconds",
                                    duration, {"provider": provider, "model": model})

    def update_budget(self, tenant_id: str, used: float, remaining: float):
        """Update budget metrics."""
        with self._lock:
            self._set_gauge("budget_used_usd", used, {"tenant_id": tenant_id})
            self._set_gauge("budget_remaining_usd", remaining, {"tenant_id": tenant_id})

    def update_queue_size(self, queue_name: str, size: int):
        """Update queue size metric."""
        with self._lock:
            self._set_gauge("queue_size", size, {"queue_name": queue_name})

    def update_active_agents(self, count: int):
        """Update active agents count."""
        with self._lock:
            self._set_gauge("active_agents", count)

    def _inc_counter(self, name: str, labels: Dict[str, str], increment: float = 1.0):
        """Increment a counter metric."""
        full_name = f"{self.prefix}{name}"
        metric = self.metrics.get(full_name)

        if metric is None:
            return

        if PROMETHEUS_AVAILABLE:
            metric.labels(**labels).inc(increment)
        else:
            label_key = tuple(sorted(labels.items()))
            if label_key not in metric["values"]:
                metric["values"][label_key] = 0
            metric["values"][label_key] += increment

    def _observe_histogram(self, name: str, value: float, labels: Dict[str, str]):
        """Observe a histogram metric."""
        full_name = f"{self.prefix}{name}"
        metric = self.metrics.get(full_name)

        if metric is None:
            return

        if PROMETHEUS_AVAILABLE:
            metric.labels(**labels).observe(value)
        else:
            label_key = tuple(sorted(labels.items()))
            if label_key not in metric["values"]:
                metric["values"][label_key] = []
            metric["values"][label_key].append(value)

    def _set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        full_name = f"{self.prefix}{name}"
        metric = self.metrics.get(full_name)

        if metric is None:
            return

        labels = labels or {}

        if PROMETHEUS_AVAILABLE:
            metric.labels(**labels).set(value)
        else:
            label_key = tuple(sorted(labels.items()))
            metric["values"][label_key] = value

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics for dashboard display."""
        summary = {}

        with self._lock:
            for name, metric in self.metrics.items():
                if PROMETHEUS_AVAILABLE:
                    # For Prometheus metrics, we'd need to collect them properly
                    # This is simplified for dashboard display
                    summary[name] = {
                        "type": type(metric).__name__.lower(),
                        "value": "Available via /metrics endpoint"
                    }
                else:
                    summary[name] = {
                        "type": metric.get("type", "unknown"),
                        "description": metric.get("description", ""),
                        "values": metric.get("values", {})
                    }

        return summary

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus client not available\n"

        from prometheus_client import generate_latest
        return generate_latest().decode('utf-8')


# Global metrics instance for easy access
metrics = EnterpriseMetrics()