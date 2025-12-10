from __future__ import annotations
from uuid import uuid4
from typing import Any, Dict, List, Optional


class NeuralState:
    """Single Source of Truth for PROJECT_HIVE runs."""

    def __init__(
        self,
        goal: str,
        mode: str = "t0",
        tenant_id: Optional[str] = None,
        budget: float = 10.0,
    ) -> None:
        self.run_id: str = str(uuid4())
        self.goal: str = goal
        self.mode: str = mode
        self.tenant_id: Optional[str] = tenant_id

        self.messages: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.artifacts: Dict[str, Any] = {}
        self.artifacts_meta: Dict[str, Dict[str, Any]] = {}

        self.step: int = 0
        self.budget: float = budget
        self.budget_used: float = 0.0

    def next_step(self) -> None:
        self.step += 1

    def add_message(
        self,
        role: str,
        content: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "NeuralState":
        msg: Dict[str, Any] = {"role": role, "content": content}
        if name:
            msg["name"] = name
        if metadata:
            msg["metadata"] = metadata
        self.messages.append(msg)
        return self

    def add_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> "NeuralState":
        self.errors.append(
            {
                "type": error_type,
                "message": message,
                "details": details or {},
            }
        )
        return self

    def add_artifact(
        self,
        key: str,
        value: Any,
        artifact_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "NeuralState":
        self.artifacts[key] = value
        if artifact_type is not None or metadata is not None:
            self.artifacts_meta[key] = {
                "artifact_type": artifact_type,
                "metadata": metadata or {},
            }
        return self

    def get_artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def update_budget(self, cost: float) -> None:
        self.budget_used += cost

    @property
    def current_phase(self) -> str:
        return f"{self.mode}_step_{self.step}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "mode": self.mode,
            "tenant_id": self.tenant_id,
            "step": self.step,
            "messages": self.messages,
            "errors": self.errors,
            "artifacts": self.artifacts,
            "artifacts_meta": self.artifacts_meta,
            "budget": self.budget,
            "budget_used": self.budget_used,
        }
