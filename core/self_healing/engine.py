from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from uuid import uuid4
from datetime import datetime

from core.self_healing.error_classifier import ErrorClassifier, ErrorType, ErrorAnalysis
from core.self_healing.repair_strategies import RepairStrategyFactory
from core.utils.logger import get_logger

logger = get_logger("SelfHealingEngine")


@dataclass
class RepairAttempt:
    attempt_id: int
    timestamp: str
    description: str
    success: bool = False


@dataclass
class HealingSession:
    session_id: str
    error_log: str
    original_code: str
    repaired_code: str
    repair_attempts: List[RepairAttempt] = field(default_factory=list)
    success: bool = False


@dataclass
class ErrorDiagnosis:
    type: ErrorType
    message: str
    details: str
    fix_prompt: str


class SelfHealingEngine:
    def __init__(self) -> None:
        self.classifier = ErrorClassifier()
        self.total_sessions: int = 0
        self.successful_sessions: int = 0

    def diagnose(self, error_log: str, code: Optional[str] = None) -> ErrorDiagnosis:
        analysis: ErrorAnalysis = self.classifier.classify(error_log)
        logger.info(
            "🔍 Diagnosed error",
            extra={"type": analysis.type.value, "details": analysis.details},
        )

        fix_prompt = RepairStrategyFactory.get_strategy(
            error_type=analysis.type,
            code=code or "",
            error=analysis.message,
        )

        return ErrorDiagnosis(
            type=analysis.type,
            message=analysis.message,
            details=analysis.details,
            fix_prompt=fix_prompt,
        )

    async def heal(
        self,
        error_log: str,
        code: str,
        context: Optional[Dict] = None,
    ) -> tuple[str, HealingSession]:
        diagnosis = self.diagnose(error_log, code)
        self.total_sessions += 1

        session_id = str(uuid4())
        attempt = RepairAttempt(
            attempt_id=1,
            timestamp=datetime.utcnow().isoformat(),
            description=f"Generated fix prompt for error type {diagnosis.type.value}",
            success=False,
        )

        session = HealingSession(
            session_id=session_id,
            error_log=error_log,
            original_code=code,
            repaired_code=code,
            repair_attempts=[attempt],
            success=False,
        )

        logger.info(
            "🛠️ Healing session created",
            extra={
                "session_id": session_id,
                "error_type": diagnosis.type.value,
                "attempts": len(session.repair_attempts),
            },
        )

        return code, session

    def get_engine_stats(self) -> Dict[str, int]:
        return {
            "total_sessions": self.total_sessions,
            "successful_sessions": self.successful_sessions,
        }
