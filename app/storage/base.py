from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fastapi import UploadFile


class Storage(ABC):
    @abstractmethod
    async def save_upload(self, file: UploadFile) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save_bytes(self, data: bytes, filename: str, content_type: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save_path(self, path: Path, filename: str | None = None, content_type: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get(self, file_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def path_for(self, file_id: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    def make_temp_dir(self) -> Path:
        raise NotImplementedError
