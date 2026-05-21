import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.storage.base import Storage


class LocalStorage(Storage):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.uploads = self.root / "uploads"
        self.outputs = self.root / "outputs"
        self.tmp = self.root / "tmp"
        for directory in (self.uploads, self.outputs, self.tmp):
            directory.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> dict[str, Any]:
        file_id = self._new_id(Path(file.filename or "upload").suffix)
        target = self.uploads / file_id
        size = 0
        with target.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                handle.write(chunk)
        return self._write_meta(target, file.filename or file_id, file.content_type, size)

    def save_bytes(self, data: bytes, filename: str, content_type: str | None = None) -> dict[str, Any]:
        file_id = self._new_id(Path(filename).suffix)
        target = self.outputs / file_id
        target.write_bytes(data)
        return self._write_meta(target, filename, content_type, len(data))

    def save_path(self, path: Path, filename: str | None = None, content_type: str | None = None) -> dict[str, Any]:
        source = Path(path)
        file_id = self._new_id(source.suffix)
        target = self.outputs / file_id
        shutil.copyfile(source, target)
        return self._write_meta(target, filename or source.name, content_type, target.stat().st_size)

    def get(self, file_id: str) -> dict[str, Any]:
        for directory in (self.uploads, self.outputs):
            path = directory / file_id
            meta_path = path.with_suffix(path.suffix + ".json")
            if path.exists() and meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["path"] = str(path)
                return meta
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "file_not_found"})

    def path_for(self, file_id: str) -> Path:
        return Path(self.get(file_id)["path"])

    def make_temp_dir(self) -> Path:
        path = self.tmp / uuid.uuid4().hex
        path.mkdir(parents=True, exist_ok=False)
        return path

    def _new_id(self, suffix: str) -> str:
        return f"{uuid.uuid4().hex}{suffix.lower()}"

    def _write_meta(self, path: Path, filename: str, content_type: str | None, size: int) -> dict[str, Any]:
        meta = {
            "file_id": path.name,
            "filename": filename,
            "content_type": content_type,
            "size": size,
        }
        path.with_suffix(path.suffix + ".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return meta
