from __future__ import annotations
from typing import Dict, Callable

from skills.code_exec.sandbox_runner import SandboxRunner


class SkillLoader:
    """Simple skill registry.

    Initially supports:
    - run_python: execute Python code in sandbox
    """

    def __init__(self) -> None:
        self.sandbox = SandboxRunner()
        self.registry: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.registry["run_python"] = self.sandbox.run_python

    def get_skill(self, name: str) -> Callable | None:
        return self.registry.get(name)
