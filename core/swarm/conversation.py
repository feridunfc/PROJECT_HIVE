from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SwarmMessage:
    role: str
    content: str
    agent_name: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

class SwarmConversation:
    def __init__(self):
        self.history: List[SwarmMessage] = []

    def add(self, role: str, content: str, agent_name: str, metadata: Dict = None):
        msg = SwarmMessage(role=role, content=content, agent_name=agent_name, metadata=metadata or {})
        self.history.append(msg)

    def get_context_window(self, limit: int = 10) -> str:
        recent = self.history[-limit:]
        return "\n".join([f"[{m.agent_name}]: {m.content}" for m in recent])

    def to_dict(self) -> List[Dict]:
        return [m.__dict__ for m in self.history]
