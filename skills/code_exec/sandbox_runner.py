from __future__ import annotations
import subprocess
import tempfile
import os
import sys
from typing import Dict, Any

from core.utils.logger import get_logger

logger = get_logger("SandboxRunner")


class SandboxRunner:
    """Executes code in a controlled subprocess environment."""

    def run_python(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        logger.info("🔒 Executing code in sandbox...")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            success = result.returncode == 0
            output = result.stdout if success else result.stderr

            logger.info(
                "Sandbox Result",
                extra={"success": success, "returncode": result.returncode},
            )
            return {"success": success, "output": output}
        except subprocess.TimeoutExpired:
            logger.error("Sandbox Timeout")
            return {"success": False, "output": "Execution timed out."}
        except Exception as e:
            logger.error(f"Sandbox Error: {e}")
            return {"success": False, "output": str(e)}
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
