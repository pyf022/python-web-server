ALL_TOOL_NAMES = (
    "archive_create",
    "archive_extract",
    "file_metadata",
    "html_to_pdf",
    "images_to_pdf",
    "json_yaml_format",
    "md_to_pdf",
    "md_to_word",
    "pdf_to_word",
    "text_extract",
    "url_screenshot",
    "webpage_to_markdown",
    "word_to_pdf",
)

FILE_RESULT_TOOLS = (
    "archive_create",
    "html_to_pdf",
    "images_to_pdf",
    "md_to_pdf",
    "md_to_word",
    "pdf_to_word",
    "word_to_pdf",
)

NON_FILE_RESULT_TOOLS = (
    "archive_extract",
    "file_metadata",
    "json_yaml_format",
    "text_extract",
    "webpage_to_markdown",
)

TOOL_NAME_HELP = (
    "支持的工具名: "
    "`md_to_word`, `md_to_pdf`, `word_to_pdf`, `pdf_to_word`, `html_to_pdf`, "
    "`text_extract`, `file_metadata`, `archive_create`, `archive_extract`, "
    "`images_to_pdf`, `webpage_to_markdown`, `url_screenshot`, `json_yaml_format`。"
)

DOWNLOAD_TOOL_HELP = (
    "适合直接下载文件流的工具: "
    "`md_to_word`, `md_to_pdf`, `word_to_pdf`, `pdf_to_word`, `html_to_pdf`, "
    "`archive_create`, `images_to_pdf`。"
)

EXTRA_INPUT_HELP = (
    "可选 JSON 字符串，会合并到工具 input 中。例如: "
    '`{"encoding":"utf-8"}`。必须是 JSON object，不能是数组或普通文本。'
)

API_KEY_HELP = "接口认证头。开发环境默认值为 `dev-api-key`，生产环境通过 `API_KEYS` 环境变量配置。"

COMMON_ERROR_RESPONSES = {
    401: {
        "description": "未提供或提供了错误的 X-API-Key。",
        "content": {
            "application/json": {
                "example": {"detail": {"code": "unauthorized", "message": "Missing or invalid X-API-Key."}}
            }
        },
    },
    404: {
        "description": "资源不存在，例如 tool_name、file_id 或 job_id 不存在。",
        "content": {"application/json": {"example": {"detail": {"code": "tool_not_found"}}}},
    },
    422: {
        "description": "入参不合法，或工具执行失败。",
        "content": {
            "application/json": {
                "example": {
                    "detail": {
                        "code": "invalid_input",
                        "message": "Missing required field: file_id",
                        "details": {},
                    }
                }
            }
        },
    },
}

CONVERT_DOWNLOAD_DESCRIPTION = f"""
一步完成上传、转换和下载。

典型场景:
- 上传 `.md` 文件，`tool_name=md_to_word`，直接下载 Word 文件。
- 上传 `.md` 文件，`tool_name=md_to_pdf`，直接下载 PDF 文件。
- 上传 `.pdf` 文件，`tool_name=pdf_to_word`，直接下载 Word 文件。
- 上传 `.docx` 文件，`tool_name=word_to_pdf`，直接下载 PDF 文件。

{DOWNLOAD_TOOL_HELP}

不适合此接口的工具: `text_extract`, `file_metadata`, `webpage_to_markdown`, `json_yaml_format`，
因为它们返回文本或 JSON，不返回文件流。需要这些工具时请使用 `/v1/tools/{{tool_name}}/run`。
"""
