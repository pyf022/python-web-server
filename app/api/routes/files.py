from fastapi import APIRouter, Depends, File, Path, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_storage, require_api_key
from app.api.docs import COMMON_ERROR_RESPONSES
from app.schemas.files import FileInfo
from app.storage.base import Storage

router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(require_api_key)])


@router.post(
    "",
    response_model=FileInfo,
    summary="上传文件",
    description="上传一个源文件到本服务，返回 `file_id`。后续可把 `file_id` 传给同步工具或异步任务接口使用。",
    response_description="上传后的文件元信息。",
    responses={401: COMMON_ERROR_RESPONSES[401]},
)
async def upload_file(
    file: UploadFile = File(..., description="要上传的文件。支持任意二进制文件，具体能否处理取决于后续选择的 tool。"),
    storage: Storage = Depends(get_storage),
) -> FileInfo:
    stored = await storage.save_upload(file)
    return FileInfo(**stored)


@router.get(
    "/{file_id}",
    summary="下载已保存文件",
    description="根据上传或工具输出得到的 `file_id` 下载文件。`file_id` 来自 `/v1/files`、同步工具结果或异步任务结果。",
    response_description="文件下载流。",
    responses={401: COMMON_ERROR_RESPONSES[401], 404: COMMON_ERROR_RESPONSES[404]},
)
def download_file(
    file_id: str = Path(..., description="文件 ID。例如上传接口返回的 `abc123.md` 或工具结果中的 `result_file_id`。"),
    storage: Storage = Depends(get_storage),
) -> FileResponse:
    stored = storage.get(file_id)
    return FileResponse(
        path=stored["path"],
        media_type=stored.get("content_type") or "application/octet-stream",
        filename=stored.get("filename") or file_id,
    )
