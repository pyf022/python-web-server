from typing import Any

from rq import get_current_job

from app.callbacks.webhook import send_webhook
from app.core.config import get_settings
from app.storage.local import LocalStorage
from app.tools.base import ToolExecutionError
from app.tools.registry import register_builtin_tools, registry


def run_tool_job(tool_name: str, input_data: dict[str, Any], callback_url: str | None = None) -> dict[str, Any]:
    job = get_current_job()
    job_id = job.id if job else None
    register_builtin_tools()
    settings = get_settings()
    storage = LocalStorage(settings.storage_root)
    tool = registry.get(tool_name)
    if not tool:
        payload = {"job_id": job_id, "status": "failed", "tool_name": tool_name, "error": {"code": "tool_not_found"}}
        _save_meta(job, payload)
        if callback_url:
            send_webhook(str(callback_url), payload)
        return payload

    try:
        if job:
            job.meta["status"] = "running"
            job.save_meta()
        result = tool.execute(input_data, storage).to_response()
        payload = {"job_id": job_id, "status": "succeeded", "tool_name": tool_name, **result}
        _save_meta(job, payload)
        if callback_url:
            send_webhook(str(callback_url), payload)
        return payload
    except ToolExecutionError as exc:
        payload = {"job_id": job_id, "status": "failed", "tool_name": tool_name, "error": exc.to_detail()}
        _save_meta(job, payload)
        if callback_url:
            send_webhook(str(callback_url), payload)
        raise


def _save_meta(job, payload: dict[str, Any]) -> None:
    if not job:
        return
    job.meta.update({k: v for k, v in payload.items() if k not in {"data"}})
    job.save_meta()
