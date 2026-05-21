from typing import Any

from pydantic import BaseModel


class JobInfo(BaseModel):
    job_id: str
    tool_name: str
    status: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
