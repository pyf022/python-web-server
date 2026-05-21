import json
from pathlib import Path

import httpx
import markdownify
import yaml
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.storage.base import Storage
from app.tools.base import BaseTool, ToolExecutionError, ToolResult
from app.tools.utils import command_exists, require_field, run_command


class WebpageToMarkdownTool(BaseTool):
    name = "webpage_to_markdown"
    description = "Fetch a web page and convert readable HTML to Markdown."
    input_schema = {"type": "object", "required": ["url"], "properties": {"url": {"type": "string"}}}

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        url = require_field(input_data, "url")
        try:
            response = httpx.get(url, follow_redirects=True, timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ToolExecutionError("fetch_failed", "Failed to fetch URL.", {"error": str(exc)}) from exc
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        markdown = markdownify.markdownify(str(soup.body or soup), heading_style="ATX")
        return ToolResult(type="text", data={"markdown": markdown, "url": str(response.url)})


class UrlScreenshotTool(BaseTool):
    name = "url_screenshot"
    description = "Capture a URL screenshot. Requires Playwright/browser dependencies if enabled."
    input_schema = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string"},
            "width": {"type": "integer", "default": 1280},
            "height": {"type": "integer", "default": 720},
        },
    }
    sync_supported = False
    timeout_seconds = 120

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        raise ToolExecutionError(
            "not_configured",
            "URL screenshots require installing Playwright browser dependencies in the worker image.",
        )


class HtmlToPdfTool(BaseTool):
    name = "html_to_pdf"
    description = "Convert HTML text or uploaded HTML file to PDF."
    input_schema = {
        "type": "object",
        "properties": {
            "html_text": {"type": "string"},
            "file_id": {"type": "string"},
            "output_filename": {"type": "string", "default": "document.pdf"},
        },
    }

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        html_text = input_data.get("html_text")
        if not html_text and input_data.get("file_id"):
            html_text = Path(storage.get(str(input_data["file_id"]))["path"]).read_text(encoding=input_data.get("encoding", "utf-8"))
        if not html_text:
            raise ToolExecutionError("invalid_input", "Provide either html_text or file_id.")
        temp_dir = storage.make_temp_dir()
        html_path = temp_dir / "input.html"
        output = temp_dir / "output.pdf"
        html_path.write_text(str(html_text), encoding="utf-8")
        if command_exists("wkhtmltopdf"):
            run_command(["wkhtmltopdf", str(html_path), str(output)], timeout=self.timeout_seconds)
        elif command_exists("pandoc"):
            run_command(["pandoc", str(html_path), "-o", str(output)], timeout=self.timeout_seconds)
        else:
            _write_text_pdf(BeautifulSoup(str(html_text), "html.parser").get_text("\n"), output)
        stored = storage.save_path(output, filename=input_data.get("output_filename") or "document.pdf", content_type="application/pdf")
        return ToolResult(type="file", result_file_id=stored["file_id"], filename=stored["filename"], content_type=stored["content_type"])


class JsonYamlFormatTool(BaseTool):
    name = "json_yaml_format"
    description = "Validate and pretty-format JSON or YAML text."
    input_schema = {
        "type": "object",
        "required": ["text", "format"],
        "properties": {
            "text": {"type": "string"},
            "format": {"type": "string", "enum": ["json", "yaml"]},
            "sort_keys": {"type": "boolean", "default": True},
        },
    }

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        text = require_field(input_data, "text")
        fmt = require_field(input_data, "format").lower()
        sort_keys = bool(input_data.get("sort_keys", True))
        try:
            if fmt == "json":
                parsed = json.loads(text)
                formatted = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=sort_keys)
            elif fmt in {"yaml", "yml"}:
                parsed = yaml.safe_load(text)
                formatted = yaml.safe_dump(parsed, allow_unicode=True, sort_keys=sort_keys)
            else:
                raise ToolExecutionError("invalid_input", "format must be json or yaml.")
        except (json.JSONDecodeError, yaml.YAMLError) as exc:
            raise ToolExecutionError("parse_failed", "Input is not valid JSON/YAML.", {"error": str(exc)}) from exc
        return ToolResult(type="text", data={"formatted": formatted})


def _write_text_pdf(text: str, output: Path) -> None:
    pdf = canvas.Canvas(str(output), pagesize=A4)
    _, height = A4
    y = height - 48
    for line in text.splitlines():
        if y < 48:
            pdf.showPage()
            y = height - 48
        pdf.drawString(48, y, line[:110])
        y -= 18
    pdf.save()
