from typing import Any

from pydantic import BaseModel, HttpUrl


class ToolInvokeRequest(BaseModel):
    input: dict[str, Any] = {}
    callback_url: HttpUrl | None = None


class ToolInvokeResponse(BaseModel):
    status: str
    result: dict[str, Any]


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    sync_supported: bool
    async_supported: bool = True
    timeout_seconds: int


class ToolListResponse(BaseModel):
    tools: list[ToolInfo]
