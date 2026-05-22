from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    file_id: str = Field(description="服务内部文件 ID。后续调用工具时把它作为 `file_id` 传入。", examples=["a1b2c3.md"])
    filename: str = Field(description="原始文件名或输出文件名。", examples=["demo.md"])
    content_type: str | None = Field(default=None, description="文件 MIME 类型。", examples=["text/markdown"])
    size: int = Field(description="文件大小，单位字节。", examples=[128])
    url: str | None = Field(default=None, description="预留下载地址字段，当前本地存储模式通常为空。", examples=[None])
