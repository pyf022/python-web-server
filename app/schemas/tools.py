from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ToolInvokeRequest(BaseModel):
    input: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "工具入参对象。不同 tool 需要不同字段，请先调用 `GET /v1/tools` 查看对应 `input_schema`。"
            "例如 `md_to_pdf` 可传 `{\"file_id\":\"xxx.md\",\"output_filename\":\"result.pdf\"}`。"
        ),
        examples=[{"file_id": "a1b2c3.md", "output_filename": "result.pdf"}],
    )
    callback_url: HttpUrl | None = Field(
        default=None,
        description="异步任务完成后的可选回调地址。只在 `/v1/tools/{tool_name}/jobs` 中使用。",
        examples=["https://example.com/tool-callback"],
    )


class ToolInvokeResponse(BaseModel):
    status: str = Field(description="同步调用状态。成功时为 `succeeded`。", examples=["succeeded"])
    result: dict[str, Any] = Field(
        description="工具执行结果。文件类工具包含 `result_file_id`，文本/JSON 类工具包含 `data`。",
        examples=[
            {
                "type": "file",
                "result_file_id": "a1b2c3.pdf",
                "filename": "result.pdf",
                "content_type": "application/pdf",
            }
        ],
    )


class JobCreateResponse(BaseModel):
    job_id: str = Field(description="异步任务 ID，后续用于查询状态和获取结果。", examples=["f8f2b19d-8d31-4f70-89e7-7ec8a10b6b28"])
    status: str = Field(description="任务初始状态。", examples=["queued"])


class ToolInfo(BaseModel):
    name: str = Field(description="工具名。调用 `/v1/tools/{tool_name}/run` 时使用该值。", examples=["md_to_pdf"])
    description: str = Field(description="工具功能说明。", examples=["Convert Markdown text or Markdown file to PDF."])
    input_schema: dict[str, Any] = Field(description="该工具的入参 JSON Schema。")
    sync_supported: bool = Field(description="是否支持同步调用 `/run`。")
    async_supported: bool = Field(default=True, description="是否支持异步任务 `/jobs`。")
    timeout_seconds: int = Field(description="该工具执行超时时间，单位秒。", examples=[300])


class ToolListResponse(BaseModel):
    tools: list[ToolInfo] = Field(description="当前服务可用工具列表。")
