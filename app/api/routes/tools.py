from fastapi import APIRouter, Depends, HTTPException, Path, status
from rq import Queue

from app.api.deps import get_queue, get_storage, require_api_key
from app.api.docs import COMMON_ERROR_RESPONSES, TOOL_NAME_HELP
from app.jobs.tasks import run_tool_job
from app.schemas.tools import JobCreateResponse, ToolInvokeRequest, ToolInvokeResponse, ToolListResponse
from app.storage.base import Storage
from app.tools.base import ToolExecutionError
from app.tools.registry import registry

router = APIRouter(prefix="/tools", tags=["tools"], dependencies=[Depends(require_api_key)])


@router.get(
    "",
    response_model=ToolListResponse,
    summary="查询全部可用工具",
    description="返回当前服务注册的所有工具、每个工具的功能说明、入参 schema、是否支持同步调用和超时时间。调用工具前建议先看这里。",
    response_description="工具列表和每个工具的 input_schema。",
    responses={401: COMMON_ERROR_RESPONSES[401]},
)
def list_tools() -> ToolListResponse:
    return ToolListResponse(tools=[tool.to_info() for tool in registry.all()])


@router.post(
    "/{tool_name}/run",
    response_model=ToolInvokeResponse,
    summary="同步执行工具",
    description=(
        "同步执行指定工具，适合小文件或短任务。`input` 的字段取决于具体工具，"
        "请先调用 `GET /v1/tools` 查看每个工具的 `input_schema`。\n\n"
        f"{TOOL_NAME_HELP}"
    ),
    response_description="工具执行结果。文件类工具返回 result_file_id，文本/JSON 类工具返回 data。",
    responses={**COMMON_ERROR_RESPONSES, 400: {"description": "工具不支持同步调用。"}},
)
def run_tool(
    request: ToolInvokeRequest,
    tool_name: str = Path(..., description=f"要执行的工具名。{TOOL_NAME_HELP}", examples=["md_to_pdf"]),
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.to_detail()) from exc

    return ToolInvokeResponse(status="succeeded", result=result.to_response())


@router.post(
    "/{tool_name}/jobs",
    response_model=JobCreateResponse,
    summary="创建异步工具任务",
    description=(
        "创建异步任务，适合大文件、耗时转换或不希望 HTTP 请求长时间等待的场景。"
        "返回 `job_id` 后，可通过 `GET /v1/jobs/{job_id}` 查询状态，"
        "通过 `GET /v1/jobs/{job_id}/result` 获取结果。\n\n"
        f"{TOOL_NAME_HELP}"
    ),
    response_description="异步任务 ID 和初始状态。",
    responses={401: COMMON_ERROR_RESPONSES[401], 404: COMMON_ERROR_RESPONSES[404]},
)
def create_job(
    request: ToolInvokeRequest,
    tool_name: str = Path(..., description=f"要异步执行的工具名。{TOOL_NAME_HELP}", examples=["pdf_to_word"]),
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
