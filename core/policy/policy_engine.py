from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from core.utils.logger import get_logger

logger = get_logger("PolicyEngine")


class PolicySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PolicyViolation:
    code: str
    message: str
    severity: PolicySeverity
    details: Optional[Dict] = None


class PolicyEngine:
    def __init__(self) -> None:
        self.banned_output_keywords = ["drop database", "rm -rf", "format c:", "key="]
        self.banned_code_patterns = ["os.system", "subprocess.Popen", "eval(", "exec("]

    def check_llm_output(self, text: str, context: Dict) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []
        lower = text.lower()
        for kw in self.banned_output_keywords:
            if kw in lower:
                violations.append(
                    PolicyViolation(
                        code="banned_keyword",
                        message=f"Output contains banned phrase: {kw}",
                        severity=PolicySeverity.HIGH,
                        details={"keyword": kw},
                    )
                )
        return violations

    def check_code(self, code: str, context: Dict) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []
        for pattern in self.banned_code_patterns:
            if pattern in code:
                violations.append(
                    PolicyViolation(
                        code="dangerous_code",
                        message=f"Code contains dangerous pattern: {pattern}",
                        severity=PolicySeverity.CRITICAL,
                        details={"pattern": pattern},
                    )
                )

        if violations:
            logger.warning(
                "Code policy violations found", extra={"count": len(violations)}
            )
        return violations
