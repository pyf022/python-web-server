from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_storage, require_api_key
from app.schemas.files import FileInfo
from app.storage.base import Storage

router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=FileInfo)
async def upload_file(file: UploadFile, storage: Storage = Depends(get_storage)) -> FileInfo:
    stored = await storage.save_upload(file)
    return FileInfo(**stored)


@router.get("/{file_id}")
def download_file(file_id: str, storage: Storage = Depends(get_storage)) -> FileResponse:
    stored = storage.get(file_id)
    return FileResponse(
        path=stored["path"],
        media_type=stored.get("content_type") or "application/octet-stream",
        filename=stored.get("filename") or file_id,
    )
