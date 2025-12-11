# core/policy/policy_engine.py
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
    """
    LLM çıktılarını ve üretilen kodu denetleyen gelişmiş güvenlik motoru.
    Import hilelerini ve tehlikeli parametreleri yakalar.
    """

    def __init__(self) -> None:
        # 1. Yasaklı Kelimeler (LLM Sohbet Çıktısı için)
        self.banned_output_keywords = [
            "drop database", "rm -rf", "format c:", "key=",
            "delete all files", "wipe disk"
        ]

        # 2. Yasaklı Kod Desenleri (Statik Analiz)
        self.banned_code_patterns = [
            # Shell Execution & Dangerous Flags
            "os.system", "shell=True", "subprocess",

            # Dynamic Execution
            "eval(", "exec(", "compile(", "__import__",

            # File System Destruction (Fonksiyonlar)
            "os.remove", "os.unlink", "os.rmdir", "shutil.rmtree",

            # File System Destruction (String Komutlar)
            "rm -rf", "del /f",

            # Network
            "socket.socket", "telnetlib",

            # System Info
            "platform.system", "getpass.getuser"
        ]

    def check_llm_output(self, text: str, context: Dict) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []
        lower = text.lower()
        for kw in self.banned_output_keywords:
            if kw in lower:
                violations.append(PolicyViolation(
                    code="banned_keyword",
                    message=f"Output contains banned phrase: {kw}",
                    severity=PolicySeverity.HIGH,
                    details={"keyword": kw}
                ))
        return violations

    def check_code(self, code: str, context: Dict) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []

        # Basit string eşleştirme
        for pattern in self.banned_code_patterns:
            if pattern in code:
                # Import hileleri için bağlam kontrolü yapılabilir ama
                # Enterprise güvenlikte "güvenli tarafta kalmak" (fail-safe) esastır.
                violations.append(PolicyViolation(
                    code="dangerous_code_pattern",
                    message=f"Security Alert: Code contains dangerous pattern: '{pattern}'",
                    severity=PolicySeverity.CRITICAL,
                    details={"pattern": pattern}
                ))

        if violations:
            logger.warning(f"🚨 Code policy violations found: {len(violations)}")
        return violations