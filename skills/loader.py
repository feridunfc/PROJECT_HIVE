from typing import Dict, Callable
from skills.code_exec.sandbox_runner import SandboxRunner

class SkillLoader:
    def __init__(self):
        self.sandbox = SandboxRunner()
        self.registry: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.registry["run_python"] = self.sandbox.run_python

    def get_skill(self, name: str) -> Callable:
        return self.registry.get(name)
