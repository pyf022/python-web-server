from fastapi import APIRouter, Depends, HTTPException, status
from rq import Queue

from app.api.deps import get_queue, get_storage, require_api_key
from app.jobs.tasks import run_tool_job
from app.schemas.tools import JobCreateResponse, ToolInvokeRequest, ToolInvokeResponse, ToolListResponse
from app.storage.base import Storage
from app.tools.base import ToolExecutionError
from app.tools.registry import registry

router = APIRouter(prefix="/tools", tags=["tools"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=ToolListResponse)
def list_tools() -> ToolListResponse:
    return ToolListResponse(tools=[tool.to_info() for tool in registry.all()])


@router.post("/{tool_name}/run", response_model=ToolInvokeResponse)
def run_tool(
    tool_name: str,
    request: ToolInvokeRequest,
    storage: Storage = Depends(get_storage),
) -> ToolInvokeResponse:
    tool = registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "tool_not_found"})
    if not tool.sync_supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "sync_not_supported"})

    try:
        result = tool.execute(request.input, storage)
    except ToolExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.to_detail()) from exc

    return ToolInvokeResponse(status="succeeded", result=result.to_response())


@router.post("/{tool_name}/jobs", response_model=JobCreateResponse)
def create_job(
    tool_name: str,
    request: ToolInvokeRequest,
    queue: Queue = Depends(get_queue),
) -> JobCreateResponse:
    tool = registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "tool_not_found"})

    job = queue.enqueue(
        run_tool_job,
        tool_name,
        request.input,
        request.callback_url,
        job_timeout=tool.timeout_seconds,
        meta={"tool_name": tool_name, "status": "queued"},
    )
    return JobCreateResponse(job_id=job.id, status="queued")
