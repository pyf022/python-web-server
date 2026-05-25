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
    input_schema = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {
                "type": "string",
                "description": "要抓取并转换为 Markdown 的网页 URL。",
                "examples": ["https://example.com/article"],
            }
        },
    }

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
    description = "Capture a URL screenshot using Playwright Chromium."
    input_schema = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {
                "type": "string",
                "description": "要截图的网页 URL。需要执行 `playwright install chromium` 安装浏览器。",
                "examples": ["https://example.com"],
            },
            "width": {"type": "integer", "description": "截图宽度，单位像素。", "default": 1280, "examples": [1280]},
            "height": {"type": "integer", "description": "截图高度，单位像素。", "default": 720, "examples": [720]},
        },
    }
    timeout_seconds = 120

    def execute(self, input_data: dict, storage: Storage) -> ToolResult:
        url = require_field(input_data, "url")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ToolExecutionError("missing_dependency", "Playwright is required for URL screenshots.") from exc
        output = storage.make_temp_dir() / "screenshot.png"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={
                        "width": int(input_data.get("width", 1280)),
                        "height": int(input_data.get("height", 720)),
                    }
                )
                page.goto(url, wait_until="networkidle", timeout=self.timeout_seconds * 1000)
                page.screenshot(path=str(output), full_page=bool(input_data.get("full_page", True)))
                browser.close()
        except Exception as exc:
            raise ToolExecutionError(
                "screenshot_failed",
                "URL screenshot failed. Verify Chromium is installed with Playwright.",
                {"error": str(exc)},
            ) from exc
        stored = storage.save_path(output, input_data.get("output_filename") or "screenshot.png", "image/png")
        return ToolResult(
            type="file",
            result_file_id=stored["file_id"],
            filename=stored["filename"],
            content_type=stored["content_type"],
        )


class HtmlToPdfTool(BaseTool):
    name = "html_to_pdf"
    description = "Convert HTML text or uploaded HTML file to PDF."
    input_schema = {
        "type": "object",
        "properties": {
            "html_text": {
                "type": "string",
                "description": "HTML 文本。`html_text` 和 `file_id` 二选一。",
                "examples": ["<h1>Hello</h1>"],
            },
            "file_id": {
                "type": "string",
                "description": "已上传的 HTML 文件 ID。`html_text` 和 `file_id` 二选一。",
                "examples": ["a1b2c3.html"],
            },
            "output_filename": {
                "type": "string",
                "description": "输出 PDF 文件名。",
                "default": "document.pdf",
                "examples": ["page.pdf"],
            },
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
            "text": {"type": "string", "description": "要校验和格式化的 JSON 或 YAML 文本。", "examples": ['{"b":1,"a":2}']},
            "format": {
                "type": "string",
                "description": "输入文本格式。",
                "enum": ["json", "yaml"],
                "examples": ["json"],
            },
            "sort_keys": {
                "type": "boolean",
                "description": "是否按 key 排序输出。",
                "default": True,
                "examples": [True],
            },
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
