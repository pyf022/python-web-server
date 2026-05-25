from app.tools.base import BaseTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all(self) -> list[BaseTool]:
        return sorted(self._tools.values(), key=lambda tool: tool.name)


registry = ToolRegistry()


def register_builtin_tools() -> None:
    if registry.all():
        return
    from app.tools.agent_tools import HtmlToPdfTool, JsonYamlFormatTool, UrlScreenshotTool, WebpageToMarkdownTool
    from app.tools.document import MarkdownToPdfTool, MarkdownToWordTool, PdfToWordTool, WordToPdfTool
    from app.tools.file_tools import (
        ArchiveCreateTool,
        ArchiveExtractTool,
        FileMetadataTool,
        ImagesToPdfTool,
        TextExtractTool,
    )
    from app.tools.integration_tools import (
        HttpRequestTool,
        JiraAddAttachmentTool,
        JiraCreateIssueTool,
        JiraGetIssueTool,
        JiraSearchIssuesTool,
        JiraTransitionIssueTool,
        SendEmailTool,
        WebpageHtmlTool,
    )
    from app.tools.knowledge_tools import (
        Bm25PreprocessTool,
        DocumentParseTool,
        ExcelParseTool,
        HtmlParseTool,
        ImageAnnotateLayoutTool,
        ImageOcrTool,
        ImageParseTool,
        MarkdownParseTool,
        PdfOcrTool,
        PdfParseTool,
        PdfToMarkdownTool,
        PptParseTool,
        TextChunkTool,
        TxtParseTool,
        WordParseTool,
        WordToMarkdownTool,
    )

    for tool in (
        WordToPdfTool(),
        PdfToWordTool(),
        MarkdownToWordTool(),
        MarkdownToPdfTool(),
        TextExtractTool(),
        FileMetadataTool(),
        ArchiveCreateTool(),
        ArchiveExtractTool(),
        ImagesToPdfTool(),
        WebpageToMarkdownTool(),
        UrlScreenshotTool(),
        HtmlToPdfTool(),
        JsonYamlFormatTool(),
        WordToMarkdownTool(),
        PdfToMarkdownTool(),
        DocumentParseTool(),
        PdfParseTool(),
        WordParseTool(),
        ExcelParseTool(),
        PptParseTool(),
        HtmlParseTool(),
        TxtParseTool(),
        MarkdownParseTool(),
        TextChunkTool(),
        Bm25PreprocessTool(),
        ImageOcrTool(),
        ImageParseTool(),
        PdfOcrTool(),
        ImageAnnotateLayoutTool(),
        HttpRequestTool(),
        WebpageHtmlTool(),
        SendEmailTool(),
        JiraSearchIssuesTool(),
        JiraGetIssueTool(),
        JiraCreateIssueTool(),
        JiraTransitionIssueTool(),
        JiraAddAttachmentTool(),
    ):
        registry.register(tool)
