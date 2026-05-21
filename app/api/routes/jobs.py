from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from rq import Queue
from rq.job import Job, JobStatus

from app.api.deps import get_queue, get_storage, require_api_key
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


@router.get("/{job_id}", response_model=JobInfo)
def get_job(job_id: str, queue: Queue = Depends(get_queue)) -> JobInfo:
    job = _fetch_job(queue, job_id)
    result = job.result if isinstance(job.result, dict) else None
    return JobInfo(
        job_id=job.id,
        tool_name=job.meta.get("tool_name", ""),
        status=_status(job),
        result=result,
        error=job.meta.get("error"),
    )


@router.get("/{job_id}/result")
def get_job_result(
    job_id: str,
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
