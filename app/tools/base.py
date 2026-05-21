from dataclasses import dataclass
from typing import Any

from app.schemas.tools import ToolInfo
from app.storage.base import Storage


class ToolExecutionError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_detail(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass
class ToolResult:
    type: str
    data: Any | None = None
    result_file_id: str | None = None
    filename: str | None = None
    content_type: str | None = None

    def to_response(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "result_file_id": self.result_file_id,
            "filename": self.filename,
            "content_type": self.content_type,
        }


class BaseTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    sync_supported = True
    timeout_seconds = 300

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        raise NotImplementedError

    def to_info(self) -> ToolInfo:
        return ToolInfo(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            sync_supported=self.sync_supported,
            timeout_seconds=self.timeout_seconds,
        )
