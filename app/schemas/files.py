from pydantic import BaseModel


class FileInfo(BaseModel):
    file_id: str
    filename: str
    content_type: str | None = None
    size: int
    url: str | None = None
