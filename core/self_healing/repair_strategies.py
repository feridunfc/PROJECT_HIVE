from core.self_healing.error_classifier import ErrorType

class RepairStrategyFactory:
    @staticmethod
    def get_strategy(error_type: ErrorType, code: str, error: str) -> str:
        base_instruction = f"Here is the code:\n```\n{code}\n```\n\nHere is the error:\n{error}\n"

        if error_type == ErrorType.SYNTAX:
            return base_instruction + "TASK: Fix the syntax error. Check indentation, colons, and brackets."
        elif error_type == ErrorType.IMPORT:
            return base_instruction + "TASK: Fix the import error. Ensure standard libraries are used or mock external deps."
        elif error_type == ErrorType.LOGIC:
            return base_instruction + "TASK: Fix the logic error. The output did not match the expectation."
        else:
            return base_instruction + "TASK: Analyze the trace and fix the code."
