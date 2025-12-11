from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime
import uuid

@dataclass
class NeuralState:
    """Global state passed between nodes in the graph engine."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    goal: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    budget: float = 100.0
    mode: str = "t0"

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role, "content": content, 
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "messages": len(self.messages),
            "artifacts": list(self.artifacts.keys())
        }
