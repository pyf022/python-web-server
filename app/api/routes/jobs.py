from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import FileResponse
from rq import Queue
from rq.job import Job, JobStatus

from app.api.deps import get_queue, get_storage, require_api_key
from app.api.docs import COMMON_ERROR_RESPONSES
from app.schemas.jobs import JobInfo
from app.storage.base import Storage

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(require_api_key)])


def _fetch_job(queue: Queue, job_id: str) -> Job:
    try:
        return Job.fetch(job_id, connection=queue.connection)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "job_not_found"}) from exc


def _status(job: Job) -> str:
    status_value = job.get_status(refresh=True)
    status_text = getattr(status_value, "value", str(status_value))
    if status_value == JobStatus.FINISHED or status_text == "finished":
        return "succeeded"
    if status_value == JobStatus.FAILED or status_text == "failed":
        return "failed"
    if status_value == JobStatus.STARTED or status_text == "started":
        return "running"
    if status_value in {JobStatus.QUEUED, JobStatus.DEFERRED, JobStatus.SCHEDULED} or status_text in {
        "queued",
        "deferred",
        "scheduled",
    }:
        return "queued"
    return status_text


@router.get(
    "/{job_id}",
    response_model=JobInfo,
    summary="查询异步任务状态",
    description="根据 `job_id` 查询异步任务状态。状态值包括 `queued`、`running`、`succeeded`、`failed`。",
    response_description="任务状态、工具名、执行结果或错误信息。",
    responses={401: COMMON_ERROR_RESPONSES[401], 404: COMMON_ERROR_RESPONSES[404]},
)
def get_job(
    job_id: str = Path(..., description="异步任务 ID，来自 `POST /v1/tools/{tool_name}/jobs` 的返回值。"),
    queue: Queue = Depends(get_queue),
) -> JobInfo:
    job = _fetch_job(queue, job_id)
    result = job.result if isinstance(job.result, dict) else None
    return JobInfo(
        job_id=job.id,
        tool_name=job.meta.get("tool_name", ""),
        status=_status(job),
        result=result,
        error=job.meta.get("error"),
    )


@router.get(
    "/{job_id}/result",
    summary="获取异步任务结果",
    description=(
        "任务成功后获取结果。文件类工具会直接返回文件流；文本或 JSON 类工具会返回 JSON。"
        "如果任务还未成功，会返回 `409 job_not_succeeded`。"
    ),
    response_description="文件下载流或 JSON 结果。",
    responses={
        401: COMMON_ERROR_RESPONSES[401],
        404: COMMON_ERROR_RESPONSES[404],
        409: {
            "description": "任务尚未成功完成。",
            "content": {"application/json": {"example": {"detail": {"code": "job_not_succeeded"}}}},
        },
    },
)
def get_job_result(
    job_id: str = Path(..., description="异步任务 ID，来自 `POST /v1/tools/{tool_name}/jobs` 的返回值。"),
    queue: Queue = Depends(get_queue),
    storage: Storage = Depends(get_storage),
):
    job = _fetch_job(queue, job_id)
    if _status(job) != "succeeded":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "job_not_succeeded"})
    if not isinstance(job.result, dict):
        return {}
    result = job.result
    file_id = result.get("result_file_id")
    if file_id:
        stored = storage.get(file_id)
        return FileResponse(
            path=stored["path"],
            media_type=stored.get("content_type") or "application/octet-stream",
            filename=stored.get("filename") or file_id,
        )
    return result
