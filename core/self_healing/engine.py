from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from core.self_healing.error_classifier import ErrorClassifier, ErrorType
from core.self_healing.repair_strategies import RepairStrategyFactory
from core.utils.logger import get_logger

logger = get_logger("SelfHealingEngine")

@dataclass
class ErrorDiagnosis:
    type: ErrorType
    message: str
    details: str
    fix_prompt: str

class SelfHealingEngine:
    def __init__(self) -> None:
        self.classifier = ErrorClassifier()

    def diagnose(self, error_log: str, code: Optional[str] = None) -> ErrorDiagnosis:
        # 1. Sınıflandır
        analysis = self.classifier.classify(error_log)
        logger.info(
            "🔍 Diagnosed error",
            extra={"type": analysis.type.value, "details": analysis.details},
        )

        # 2. Strateji Belirle
        code_str = code or ""
        fix_prompt = RepairStrategyFactory.get_strategy(
            error_type=analysis.type,
            code=code_str,
            error=analysis.message,
        )

        return ErrorDiagnosis(
            type=analysis.type,
            message=analysis.message,
            details=analysis.details,
            fix_prompt=fix_prompt,
        )
