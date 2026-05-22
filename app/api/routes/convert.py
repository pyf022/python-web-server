import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_storage, require_api_key
from app.api.docs import COMMON_ERROR_RESPONSES, CONVERT_DOWNLOAD_DESCRIPTION, DOWNLOAD_TOOL_HELP, EXTRA_INPUT_HELP
from app.storage.base import Storage
from app.tools.base import ToolExecutionError
from app.tools.registry import registry

router = APIRouter(prefix="/convert", tags=["convert"], dependencies=[Depends(require_api_key)])


@router.post(
    "/download",
    summary="一步上传转换并下载结果文件",
    description=CONVERT_DOWNLOAD_DESCRIPTION,
    response_description="转换成功后的文件下载流。",
    responses={
        **COMMON_ERROR_RESPONSES,
        200: {
            "description": "转换成功，直接返回文件流。响应头 Content-Disposition 会携带下载文件名。",
            "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
        },
        400: {
            "description": "选择的工具不支持同步执行。",
            "content": {"application/json": {"example": {"detail": {"code": "sync_not_supported"}}}},
        },
    },
)
async def convert_and_download(
    file: UploadFile = File(..., description="要转换的源文件。例如 `.md`, `.pdf`, `.docx`, `.html`, `.png`。"),
    tool_name: str = Form(..., description=f"要执行的工具名。{DOWNLOAD_TOOL_HELP}", examples=["md_to_word"]),
    output_filename: str | None = Form(
        default=None,
        description="可选输出文件名，只对文件输出类工具有效。例如 `result.docx`、`result.pdf`。",
        examples=["result.docx"],
    ),
    extra_input: str | None = Form(default=None, description=EXTRA_INPUT_HELP, examples=['{"encoding":"utf-8"}']),
    storage: Storage = Depends(get_storage),
) -> FileResponse:
    tool = registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "tool_not_found"})
    if not tool.sync_supported:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "sync_not_supported"})

    uploaded = await storage.save_upload(file)
    input_data = _parse_extra_input(extra_input)
    input_data["file_id"] = uploaded["file_id"]
    if output_filename:
        input_data["output_filename"] = output_filename

    try:
        result = tool.execute(input_data, storage)
    except ToolExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.to_detail()) from exc

    if result.type != "file" or not result.result_file_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "tool_did_not_return_file", "message": "The selected tool did not return a downloadable file."},
        )

    stored = storage.get(result.result_file_id)
    return FileResponse(
        path=stored["path"],
        media_type=result.content_type or stored.get("content_type") or "application/octet-stream",
        filename=result.filename or stored.get("filename") or result.result_file_id,
    )


def _parse_extra_input(extra_input: str | None) -> dict[str, Any]:
    if not extra_input:
        return {}
    try:
        parsed = json.loads(extra_input)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_extra_input", "message": "extra_input must be a valid JSON object."},
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_extra_input", "message": "extra_input must be a JSON object."},
        )
    return parsed
