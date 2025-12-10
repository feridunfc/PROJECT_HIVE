from enum import Enum
from dataclasses import dataclass
from core.utils.logger import get_logger

logger=get_logger("Healing")

class ErrorType(Enum):
    SYNTAX="syntax"; IMPORT="import"; LOGIC="logic"; UNKNOWN="unknown"

@dataclass
class ErrorDiagnosis:
    type:ErrorType; message:str; suggestion:str

class SelfHealingEngine:
    def diagnose(self,log:str):
        l=log.lower()
        if "syntax" in l: return ErrorDiagnosis(ErrorType.SYNTAX,log,"Fix syntax")
        if "import" in l: return ErrorDiagnosis(ErrorType.IMPORT,log,"Fix import")
        if "assert" in l: return ErrorDiagnosis(ErrorType.LOGIC,log,"Fix logic")
        return ErrorDiagnosis(ErrorType.UNKNOWN,log,"General fix")
