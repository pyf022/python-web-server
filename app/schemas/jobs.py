from typing import Any

from pydantic import BaseModel, Field


class JobInfo(BaseModel):
    job_id: str = Field(description="异步任务 ID。", examples=["f8f2b19d-8d31-4f70-89e7-7ec8a10b6b28"])
    tool_name: str = Field(description="执行该任务的工具名。", examples=["md_to_pdf"])
    status: str = Field(description="任务状态: queued, running, succeeded, failed。", examples=["succeeded"])
    result: dict[str, Any] | None = Field(default=None, description="任务成功后的结果。文件类工具会包含 `result_file_id`。")
    error: dict[str, Any] | None = Field(default=None, description="任务失败时的错误信息。")
