import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from app.tools.base import ToolExecutionError


def require_field(input_data: dict, key: str) -> str:
    value = input_data.get(key)
    if not value:
        raise ToolExecutionError("invalid_input", f"Missing required field: {key}")
    return str(value)


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_command(args: Sequence[str], cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolExecutionError("command_timeout", f"Command timed out after {timeout} seconds.") from exc
    if completed.returncode != 0:
        raise ToolExecutionError(
            "command_failed",
            "External conversion command failed.",
            {"args": list(args), "stderr": completed.stderr[-4000:]},
        )
    return completed


def detect_content_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".zip": "application/zip",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(suffix, "application/octet-stream")
