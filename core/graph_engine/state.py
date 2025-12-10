from __future__ import annotations
from uuid import uuid4
from typing import Any, Dict, List, Optional

class NeuralState:
    """
    Tek kaynaklı gerçek durum objesi (Single Source of Truth).
    Enterprise uyumlu: Telemetri, Hata takibi ve Bütçe içerir.
    """

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

        self.step: int = 0
        self.budget: float = budget
        self.budget_used: float = 0.0

    # --- Flow control ---
    def next_step(self) -> None:
        self.step += 1

    # --- Messages ---
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

    # --- Errors ---
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

    # --- Artifacts ---
    def add_artifact(self, key: str, value: Any) -> "NeuralState":
        self.artifacts[key] = value
        return self

    # --- Budget ---
    def update_budget(self, cost: float) -> None:
        self.budget_used += cost

    # --- Serialization ---
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
            "budget": self.budget,
            "budget_used": self.budget_used,
        }
