import json
import zipfile
from pathlib import Path

from docx import Document
from PIL import Image
from pypdf import PdfReader

from app.storage.base import Storage
from app.tools.base import BaseTool, ToolExecutionError, ToolResult
from app.tools.utils import detect_content_type, require_field


class TextExtractTool(BaseTool):
    name = "text_extract"
    description = "Extract text from TXT, Markdown, PDF, or DOCX files."
    input_schema = {"type": "object", "required": ["file_id"], "properties": {"file_id": {"type": "string"}}}

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        file_id = require_field(input_data, "file_id")
        path = storage.path_for(file_id)
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".json", ".yaml", ".yml", ".html"}:
            text = path.read_text(encoding=input_data.get("encoding", "utf-8"))
        elif suffix == ".pdf":
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix == ".docx":
            document = Document(str(path))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        else:
            raise ToolExecutionError("unsupported_file_type", f"Text extraction is not supported for {suffix}.")
        return ToolResult(type="text", data={"text": text})


class FileMetadataTool(BaseTool):
    name = "file_metadata"
    description = "Return stored file metadata."
    input_schema = {"type": "object", "required": ["file_id"], "properties": {"file_id": {"type": "string"}}}

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        meta = storage.get(require_field(input_data, "file_id")).copy()
        meta.pop("path", None)
        meta["detected_content_type"] = detect_content_type(meta["filename"])
        return ToolResult(type="json", data=meta)


class ArchiveCreateTool(BaseTool):
    name = "archive_create"
    description = "Create a ZIP archive from stored file IDs."
    input_schema = {
        "type": "object",
        "required": ["file_ids"],
        "properties": {"file_ids": {"type": "array", "items": {"type": "string"}}, "output_filename": {"type": "string"}},
    }

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        file_ids = input_data.get("file_ids")
        if not isinstance(file_ids, list) or not file_ids:
            raise ToolExecutionError("invalid_input", "file_ids must be a non-empty list.")
        output_filename = input_data.get("output_filename") or "archive.zip"
        temp_dir = storage.make_temp_dir()
        output = temp_dir / "archive.zip"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_id in file_ids:
                meta = storage.get(str(file_id))
                archive.write(meta["path"], arcname=meta["filename"])
        stored = storage.save_path(output, filename=output_filename, content_type="application/zip")
        return ToolResult(type="file", result_file_id=stored["file_id"], filename=stored["filename"], content_type=stored["content_type"])


class ArchiveExtractTool(BaseTool):
    name = "archive_extract"
    description = "Extract a ZIP archive and return extracted files."
    input_schema = {"type": "object", "required": ["file_id"], "properties": {"file_id": {"type": "string"}}}

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        path = storage.path_for(require_field(input_data, "file_id"))
        if path.suffix.lower() != ".zip":
            raise ToolExecutionError("invalid_input", "archive_extract expects a .zip file.")
        temp_dir = storage.make_temp_dir()
        extracted: list[dict] = []
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                target = temp_dir / Path(member.filename).name
                target.write_bytes(archive.read(member))
                stored = storage.save_path(target, filename=Path(member.filename).name, content_type=detect_content_type(member.filename))
                extracted.append({k: stored[k] for k in ("file_id", "filename", "content_type", "size")})
        return ToolResult(type="json", data={"files": extracted})


class ImagesToPdfTool(BaseTool):
    name = "images_to_pdf"
    description = "Convert one or more image files to a single PDF."
    input_schema = {
        "type": "object",
        "required": ["file_ids"],
        "properties": {"file_ids": {"type": "array", "items": {"type": "string"}}, "output_filename": {"type": "string"}},
    }

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        file_ids = input_data.get("file_ids")
        if not isinstance(file_ids, list) or not file_ids:
            raise ToolExecutionError("invalid_input", "file_ids must be a non-empty list.")
        images = []
        for file_id in file_ids:
            image = Image.open(storage.path_for(str(file_id))).convert("RGB")
            images.append(image)
        temp_dir = storage.make_temp_dir()
        output = temp_dir / "images.pdf"
        images[0].save(output, save_all=True, append_images=images[1:])
        stored = storage.save_path(output, filename=input_data.get("output_filename") or "images.pdf", content_type="application/pdf")
        return ToolResult(type="file", result_file_id=stored["file_id"], filename=stored["filename"], content_type=stored["content_type"])
