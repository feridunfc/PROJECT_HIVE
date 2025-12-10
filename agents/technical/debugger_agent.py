from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from agents.base.base_agent import BaseAgent, AgentConfig
from core.graph_engine.state import NeuralState
from core.self_healing.engine import SelfHealingEngine
from core.utils.logger import get_logger


class DebuggerAgent(BaseAgent):
    """Advanced Debugger Agent with self-healing capabilities."""

    def __init__(self, enable_auto_heal: bool = True) -> None:
        config = AgentConfig(
            name="DebuggerAgent",
            role="Senior Debugger & Code Fixer",
            goal="Analyze and fix errors in generated code through systematic debugging and self-healing",
            backstory=(
                "You are an expert debugger with years of experience in fixing complex software issues. "
                "You methodically analyze error logs, understand root causes, and apply precise fixes. "
                "You have deep knowledge of multiple programming languages and debugging techniques."
            ),
            capabilities=[
                "Error log analysis",
                "Stack trace interpretation",
                "Code pattern recognition",
                "Automatic code repair",
                "Test-driven debugging",
                "Performance issue diagnosis",
            ],
            constraints=[
                "Always prioritize security when suggesting fixes",
                "Maintain code readability and standards",
                "Consider performance implications of fixes",
                "Document complex fixes with comments",
                "Respect existing code architecture",
            ],
            tools=["self_healing_engine", "code_analyzer", "test_runner"],
            max_retries=3,
            timeout=60,
        )
        super().__init__(config)
        self.enable_auto_heal = enable_auto_heal
        self.healing_engine = SelfHealingEngine()
        self.debugging_stats: Dict[str, Any] = {
            "errors_analyzed": 0,
            "fixes_suggested": 0,
            "auto_heals_attempted": 0,
            "auto_heals_successful": 0,
            "common_error_patterns": {},
        }
        self.logger = get_logger("Agent.DebuggerAgent")

    async def execute(self, state: NeuralState) -> NeuralState:
        context = await self._observe(state)
        thoughts = await self._think(state, context)
        result = await self._act(state, thoughts)
        state = await self._reflect(state, result)
        return state

    async def _build_user_prompt(self, state: NeuralState) -> str:
        return "DebuggerAgent does not use LLM-based user prompts currently."

    async def _observe(self, state: NeuralState) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "run_id": state.run_id,
            "step": state.step,
            "phase": getattr(state, "current_phase", None),
            "goal": state.goal,
            "errors": state.errors[-5:] if state.errors else [],
            "artifacts": list(state.artifacts.keys()),
            "recent_messages": [
                msg for msg in state.messages[-3:] if msg.get("name") != self.config.name
            ],
        }

        test_results = state.get_artifact("test_results")
        if isinstance(test_results, Dict):
            context["test_results"] = {
                "success": test_results.get("success", False),
                "output": str(test_results.get("output", ""))[:500],
                "error_count": test_results.get("error_count", 0),
            }

        generated_code = state.get_artifact("generated_code", {})
        if isinstance(generated_code, Dict) and generated_code:
            context["code_summary"] = {
                "file_count": len(generated_code),
                "file_names": list(generated_code.keys()),
                "total_lines": sum(len(str(code).split("\n")) for code in generated_code.values()),
            }

        self.logger.debug(
            "Debug context collected",
            extra={
                "run_id": state.run_id,
                "error_count": len(context.get("errors", [])),
                "has_test_results": "test_results" in context,
            },
        )

        return context

    async def _think(self, state: NeuralState, context: Dict[str, Any]) -> Dict[str, Any]:
        thoughts: Dict[str, Any] = {
            "needs_attention": False,
            "error_types": [],
            "suggested_approach": "monitoring",
            "priority": "low",
        }

        if context.get("errors"):
            thoughts["needs_attention"] = True
            thoughts["error_types"] = [e.get("type", "unknown") for e in context["errors"]]
            thoughts["suggested_approach"] = "analysis"
            thoughts["priority"] = "high"

        test_results = context.get("test_results")
        if isinstance(test_results, Dict) and not test_results.get("success", True):
            thoughts["needs_attention"] = True
            thoughts["suggested_approach"] = "fixing"
            thoughts["priority"] = "critical"

            test_output = str(test_results.get("output", "")).lower()
            if any(pattern in test_output for pattern in ["assert", "fail", "error"]):
                thoughts["error_types"].append("test_failure")

        if thoughts["needs_attention"]:
            for error_type in thoughts["error_types"]:
                self.debugging_stats["common_error_patterns"][error_type] = (
                    self.debugging_stats["common_error_patterns"].get(error_type, 0) + 1
                )

        self.logger.info(
            "Debugging thoughts formulated",
            extra={
                "run_id": state.run_id,
                "needs_attention": thoughts["needs_attention"],
                "approach": thoughts["suggested_approach"],
                "priority": thoughts["priority"],
            },
        )

        return thoughts

    async def _act(self, state: NeuralState, thoughts: Dict[str, Any]) -> Dict[str, Any]:
        actions_taken: List[str] = []
        results: Dict[str, Any] = {}

        if not thoughts.get("needs_attention"):
            actions_taken.append("monitoring")
            results["status"] = "no_action_needed"
            results["message"] = "No errors detected, continuing monitoring"
            return {"actions": actions_taken, "results": results}

        analysis_result = await self._analyze_errors(state, thoughts)
        actions_taken.append("error_analysis")
        results["analysis"] = analysis_result

        if (
            self.enable_auto_heal
            and thoughts.get("suggested_approach") == "fixing"
            and analysis_result.get("can_auto_heal")
        ):
            heal_result = await self._attempt_auto_heal(state, analysis_result)
            actions_taken.append("auto_healing")
            results["healing"] = heal_result

            self.debugging_stats["auto_heals_attempted"] += 1
            if heal_result.get("success"):
                self.debugging_stats["auto_heals_successful"] += 1

        self.debugging_stats["errors_analyzed"] += 1
        self.debugging_stats["fixes_suggested"] += len(actions_taken)

        results["actions_taken"] = actions_taken
        results["debugging_stats"] = dict(self.debugging_stats)

        self.logger.info(
            "Debugging actions executed",
            extra={
                "run_id": state.run_id,
                "actions": actions_taken,
                "auto_heal_attempted": "auto_healing" in actions_taken,
            },
        )

        return {"actions": actions_taken, "results": results}

    async def _analyze_errors(self, state: NeuralState, thoughts: Dict[str, Any]) -> Dict[str, Any]:
        analysis: Dict[str, Any] = {
            "error_count": len(state.errors),
            "critical_errors": 0,
            "common_patterns": [],
            "root_cause_hypotheses": [],
            "can_auto_heal": False,
            "suggested_fixes": [],
        }

        for error in state.errors[-5:]:
            error_type = error.get("type", "unknown")
            severity = error.get("severity", "medium")
            message = str(error.get("message", ""))

            if severity == "critical":
                analysis["critical_errors"] += 1

            pattern = self._extract_error_pattern(message)
            if pattern:
                analysis["common_patterns"].append(pattern)

            hypothesis = self._generate_hypothesis(error_type, message)
            if hypothesis:
                analysis["root_cause_hypotheses"].append(hypothesis)

            fixes = self._suggest_fixes(error_type, message)
            analysis["suggested_fixes"].extend(fixes)

        test_results = state.get_artifact("test_results")
        generated_code = state.get_artifact("generated_code", {})

        if (
            isinstance(test_results, Dict)
            and not test_results.get("success")
            and isinstance(generated_code, Dict)
            and len(generated_code) == 1
        ):
            analysis["can_auto_heal"] = True
            analysis["auto_heal_reason"] = "Single file with test failures detected"

        return analysis

    def _extract_error_pattern(self, message: str) -> Optional[str]:
        lower = message.lower()
        if "syntax" in lower:
            return "syntax_error"
        if "import" in lower:
            return "import_error"
        if "assert" in lower or "failed" in lower:
            return "assertion_failure"
        return None

    def _generate_hypothesis(self, error_type: str, message: str) -> Optional[str]:
        if error_type == "syntax_error":
            return "There is likely a missing colon, bracket, or indentation issue."
        if error_type == "import_error":
            return "A required module may not be installed or the import path is incorrect."
        if "assert" in message.lower():
            return "The implementation does not match the expected behavior from tests."
        return None

    def _suggest_fixes(self, error_type: str, message: str) -> List[str]:
        suggestions: List[str] = []
        lower = message.lower()
        if "division by zero" in lower:
            suggestions.append("Add a check to avoid dividing by zero.")
        if "index out of range" in lower:
            suggestions.append("Add bounds checking before accessing list indices.")
        if "keyerror" in lower:
            suggestions.append("Use dict.get() or check key existence before access.")
        return suggestions

    async def _attempt_auto_heal(self, state: NeuralState, analysis: Dict[str, Any]) -> Dict[str, Any]:
        heal_result: Dict[str, Any] = {
            "attempted": True,
            "success": False,
            "method": "unknown",
            "details": {},
        }

        try:
            generated_code = state.get_artifact("generated_code", {})
            if not isinstance(generated_code, Dict) or not generated_code:
                heal_result["error"] = "No generated code found"
                return heal_result

            test_results = state.get_artifact("test_results", {})
            error_log = str(test_results.get("output", "Test failure"))

            code_file, original_code = next(iter(generated_code.items()))

            self.logger.info(
                "Attempting auto-heal",
                extra={
                    "run_id": state.run_id,
                    "code_file": code_file,
                    "code_length": len(str(original_code)),
                    "error_preview": error_log[:100],
                },
            )

            healed_code, healing_session = await self.healing_engine.heal(
                error_log=error_log,
                code=str(original_code),
                context={
                    "code_file": code_file,
                    "test_results": test_results,
                    "analysis": analysis,
                },
            )

            heal_result["success"] = getattr(healing_session, "success", False)
            heal_result["method"] = "self_healing_engine"
            heal_result["details"] = {
                "session_id": getattr(healing_session, "session_id", "")[:8],
                "attempts": len(getattr(healing_session, "repair_attempts", [])),
                "code_changed": str(original_code) != healed_code,
                "final_code_length": len(healed_code),
            }

            if healing_session.success:
                state.add_artifact(
                    key="generated_code",
                    value={code_file: healed_code},
                    artifact_type="healed_code",
                    metadata={
                        "healing_session": healing_session.session_id,
                        "original_length": len(str(original_code)),
                        "healed_at": datetime.utcnow().isoformat(),
                    },
                )

                if "test_results" in state.artifacts:
                    del state.artifacts["test_results"]

                self.logger.info(
                    "Auto-heal successful",
                    extra={
                        "run_id": state.run_id,
                        "session_id": healing_session.session_id[:8],
                        "attempts": len(healing_session.repair_attempts),
                    },
                )
            else:
                self.logger.warning(
                    "Auto-heal ended without success",
                    extra={
                        "run_id": state.run_id,
                        "session_id": getattr(healing_session, "session_id", "")[:8],
                        "attempts": len(getattr(healing_session, "repair_attempts", [])),
                    },
                )

        except Exception as e:
            heal_result["error"] = str(e)
            self.logger.error(
                "Auto-heal attempt crashed",
                extra={"run_id": state.run_id, "error": str(e)},
                exc_info=True,
            )

        return heal_result

    async def _reflect(self, state: NeuralState, result: Dict[str, Any]) -> NeuralState:
        actions = result.get("actions", [])
        results = result.get("results", {})

        debug_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": state.step,
            "actions_taken": actions,
            "analysis": results.get("analysis", {}),
            "healing": results.get("healing", {}),
            "debugging_stats": dict(self.debugging_stats),
            "healing_engine_stats": self.healing_engine.get_engine_stats(),
        }

        state.add_artifact(
            key=f"debug_report_step_{state.step}",
            value=debug_report,
            artifact_type="debug_report",
        )

        if "auto_healing" in actions:
            heal_result = results.get("healing", {})
            if heal_result.get("success"):
                message = "✅ Auto-healing successful! Fixed code using self-healing engine."
            else:
                message = "⚠️ Auto-healing attempted but failed. Manual review recommended."
        elif "error_analysis" in actions:
            analysis = results.get("analysis", {})
            if analysis.get("critical_errors", 0) > 0:
                message = f"🚨 Critical errors detected! {analysis.get('error_count', 0)} errors found."
            else:
                message = f"🔍 Error analysis complete. Found {analysis.get('error_count', 0)} errors."
        else:
            message = "👁️ Monitoring active. No issues detected."

        state.add_message(
            role="assistant",
            content=message,
            name=self.config.name,
        )

        return state
