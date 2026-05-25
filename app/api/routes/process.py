import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_storage, require_api_key
from app.schemas.tools import ToolInvokeResponse
from app.storage.base import Storage
from app.tools.base import ToolExecutionError
from app.tools.registry import registry

router = APIRouter(prefix="/process", tags=["process"], dependencies=[Depends(require_api_key)])


@router.post(
    "/run",
    response_model=ToolInvokeResponse,
    summary="上传文件并直接执行解析/OCR 工具",
    description=(
        "适合 `document_parse`、`image_ocr`、`pdf_ocr`、`image_annotate_layout` 等上传后返回 JSON/文本的工具。"
        "上传文件会自动注入为 `file_id`；其他参数通过 `extra_input` JSON 字符串传递。"
    ),
    response_description="工具执行结果，可能包含文本、结构化 JSON，或附带生成文件的 result_file_id。",
)
async def upload_and_process(
    file: UploadFile = File(..., description="需要解析或识别的源文件。"),
    tool_name: str = Form(
        ...,
        description="推荐值: document_parse, image_ocr, pdf_ocr, image_annotate_layout, word_to_md, pdf_to_md。",
        examples=["document_parse"],
    ),
    extra_input: str | None = Form(
        default=None,
        description='可选 JSON object 字符串。例如 `{"language":"chi_sim+eng"}`。',
        examples=['{"language":"chi_sim+eng"}'],
    ),
    storage: Storage = Depends(get_storage),
) -> ToolInvokeResponse:
    tool = registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "tool_not_found"})
    if not tool.sync_supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "sync_not_supported"})
    uploaded = await storage.save_upload(file)
    input_data = _parse_extra_input(extra_input)
    input_data["file_id"] = uploaded["file_id"]
    try:
        result = tool.execute(input_data, storage)
    except ToolExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.to_detail()) from exc
    return ToolInvokeResponse(status="succeeded", result=result.to_response())


def _parse_extra_input(extra_input: str | None) -> dict[str, Any]:
    if not extra_input:
        return {}
    try:
        parsed = json.loads(extra_input)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_extra_input", "message": "extra_input must be a valid JSON object."},
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_extra_input", "message": "extra_input must be a JSON object."},
        )
    return parsed
