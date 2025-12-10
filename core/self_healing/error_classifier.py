import re
from enum import Enum
from dataclasses import dataclass

class ErrorType(Enum):
    SYNTAX = "syntax"
    IMPORT = "import"
    LOGIC = "logic"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

@dataclass
class ErrorAnalysis:
    type: ErrorType
    message: str
    details: str

class ErrorClassifier:
    PATTERNS = {
        ErrorType.SYNTAX: [r"SyntaxError", r"IndentationError", r"TabError"],
        ErrorType.IMPORT: [r"ImportError", r"ModuleNotFoundError"],
        ErrorType.TIMEOUT: [r"TimeoutError", r"time limit exceeded"],
        ErrorType.LOGIC: [r"AssertionError", r"failed", r"mismatch"]
    }

    def classify(self, error_log: str) -> ErrorAnalysis:
        for err_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_log, re.IGNORECASE):
                    return ErrorAnalysis(type=err_type, message=error_log, details=f"Matched {pattern}")
        return ErrorAnalysis(type=ErrorType.UNKNOWN, message=error_log, details="No pattern matched")
