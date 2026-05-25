import json
import mimetypes
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx

from app.storage.base import Storage
from app.tools.base import BaseTool, ToolExecutionError, ToolResult
from app.tools.utils import require_field


class HttpRequestTool(BaseTool):
    name = "http_request"
    description = "Send an HTTP request for agent integrations and return response data."
    input_schema = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string", "description": "请求 URL。", "examples": ["https://example.com/api"]},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"], "default": "GET"},
            "headers": {"type": "object", "default": {}},
            "params": {"type": "object", "default": {}},
            "json": {"type": "object"},
            "data": {"type": "object"},
            "timeout_seconds": {"type": "number", "default": 20},
        },
    }

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        url = require_field(input_data, "url")
        method = str(input_data.get("method", "GET")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ToolExecutionError("invalid_input", "Unsupported HTTP method.")
        try:
            response = httpx.request(
                method,
                url,
                headers=input_data.get("headers") or {},
                params=input_data.get("params") or {},
                json=input_data.get("json"),
                data=input_data.get("data"),
                follow_redirects=True,
                timeout=float(input_data.get("timeout_seconds", 20)),
            )
        except httpx.HTTPError as exc:
            raise ToolExecutionError("request_failed", "HTTP request failed.", {"error": str(exc)}) from exc
        content_type = response.headers.get("content-type", "")
        body: Any
        if "application/json" in content_type:
            try:
                body = response.json()
            except ValueError:
                body = response.text
        else:
            body = response.text
        return ToolResult(
            type="json",
            data={
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url),
                "body": body,
            },
        )


class WebpageHtmlTool(BaseTool):
    name = "webpage_to_html"
    description = "Fetch a web page and return raw or cleaned HTML."
    input_schema = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string", "description": "目标网页 URL。"},
            "remove_scripts": {"type": "boolean", "default": True},
        },
    }

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        try:
            response = httpx.get(require_field(input_data, "url"), follow_redirects=True, timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ToolExecutionError("fetch_failed", "Failed to fetch page HTML.", {"error": str(exc)}) from exc
        html = response.text
        if input_data.get("remove_scripts", True):
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            html = str(soup)
        return ToolResult(type="text", data={"url": str(response.url), "html": html})


class SendEmailTool(BaseTool):
    name = "send_email_smtp"
    description = "Send an email via a supplied SMTP configuration."
    input_schema = {
        "type": "object",
        "required": ["subject", "message_body", "recipient_email", "smtp_config"],
        "properties": {
            "subject": {"type": "string", "description": "邮件主题。"},
            "message_body": {"type": "string", "description": "邮件正文。"},
            "recipient_email": {"type": "string", "description": "收件人邮箱。"},
            "attachment_file_ids": {"type": "array", "items": {"type": "string"}},
            "smtp_config": {
                "type": "object",
                "description": "SMTP 配置，包括 sender_email, sender_password, smtp_server, smtp_port, use_ssl。",
            },
        },
    }
    timeout_seconds = 120

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        config = input_data.get("smtp_config")
        if not isinstance(config, dict):
            raise ToolExecutionError("invalid_input", "smtp_config must be an object.")
        sender = str(config.get("sender_email") or "")
        password = str(config.get("sender_password") or config.get("sender_auth_code") or "")
        server = str(config.get("smtp_server") or "")
        if not sender or not password or not server:
            raise ToolExecutionError("invalid_input", "smtp_config requires sender_email, sender_password, and smtp_server.")
        message = EmailMessage()
        message["Subject"] = require_field(input_data, "subject")
        message["From"] = config.get("display_name") or sender
        message["To"] = require_field(input_data, "recipient_email")
        message.set_content(require_field(input_data, "message_body"))
        for file_id in input_data.get("attachment_file_ids") or []:
            meta = storage.get(str(file_id))
            content_type, _ = mimetypes.guess_type(meta["filename"])
            maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
            message.add_attachment(
                storage.path_for(str(file_id)).read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=meta["filename"],
            )
        try:
            smtp_port = int(config.get("smtp_port", 465 if config.get("use_ssl", True) else 587))
            smtp_cls = smtplib.SMTP_SSL if config.get("use_ssl", True) else smtplib.SMTP
            with smtp_cls(server, smtp_port, timeout=20) as smtp:
                if not config.get("use_ssl", True) and config.get("starttls", True):
                    smtp.starttls()
                smtp.login(sender, password)
                smtp.send_message(message)
        except Exception as exc:
            raise ToolExecutionError("email_failed", "SMTP email delivery failed.", {"error": str(exc)}) from exc
        return ToolResult(type="json", data={"sent": True, "recipient_email": message["To"]})


def _jira_client(input_data: dict[str, Any]) -> tuple[httpx.Client, str]:
    config = input_data.get("jira_config")
    if not isinstance(config, dict):
        raise ToolExecutionError("invalid_input", "jira_config must be an object.")
    base_url = str(config.get("base_url") or "").rstrip("/")
    if not base_url:
        raise ToolExecutionError("invalid_input", "jira_config.base_url is required.")
    headers = {"Accept": "application/json"}
    auth = None
    if config.get("api_token") and config.get("email"):
        auth = (str(config["email"]), str(config["api_token"]))
    elif config.get("bearer_token"):
        headers["Authorization"] = f"Bearer {config['bearer_token']}"
    else:
        raise ToolExecutionError("invalid_input", "Provide jira_config email/api_token or bearer_token.")
    return httpx.Client(base_url=base_url, headers=headers, auth=auth, timeout=30), base_url


class JiraSearchIssuesTool(BaseTool):
    name = "jira_search_issues"
    description = "Search Jira issues using JQL."
    input_schema = {
        "type": "object",
        "required": ["jira_config", "jql"],
        "properties": {
            "jira_config": {"type": "object", "description": "Jira base_url and authentication."},
            "jql": {"type": "string", "examples": ["project = LLMAG ORDER BY created DESC"]},
            "max_results": {"type": "integer", "default": 50},
        },
    }

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        client, _ = _jira_client(input_data)
        try:
            response = client.get(
                "/rest/api/3/search",
                params={"jql": require_field(input_data, "jql"), "maxResults": int(input_data.get("max_results", 50))},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ToolExecutionError("jira_request_failed", "Jira issue search failed.", {"error": str(exc)}) from exc
        finally:
            client.close()
        return ToolResult(type="json", data=response.json())


class JiraGetIssueTool(BaseTool):
    name = "jira_get_issue"
    description = "Fetch a Jira issue by issue key."
    input_schema = {
        "type": "object",
        "required": ["jira_config", "issue_key"],
        "properties": {
            "jira_config": {"type": "object"},
            "issue_key": {"type": "string", "examples": ["LLMAG-6"]},
        },
    }

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        return _jira_json_request(input_data, "GET", f"/rest/api/3/issue/{require_field(input_data, 'issue_key')}")


class JiraCreateIssueTool(BaseTool):
    name = "jira_create_issue"
    description = "Create a Jira issue using Jira REST fields."
    input_schema = {
        "type": "object",
        "required": ["jira_config", "fields"],
        "properties": {"jira_config": {"type": "object"}, "fields": {"type": "object", "description": "Jira issue fields payload."}},
    }

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        if not isinstance(input_data.get("fields"), dict):
            raise ToolExecutionError("invalid_input", "fields must be an object.")
        return _jira_json_request(input_data, "POST", "/rest/api/3/issue", {"fields": input_data["fields"]})


class JiraTransitionIssueTool(BaseTool):
    name = "jira_transition_issue"
    description = "Transition a Jira issue status."
    input_schema = {
        "type": "object",
        "required": ["jira_config", "issue_key", "transition_id"],
        "properties": {
            "jira_config": {"type": "object"},
            "issue_key": {"type": "string"},
            "transition_id": {"type": "string"},
        },
    }

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        issue_key = require_field(input_data, "issue_key")
        payload = {"transition": {"id": require_field(input_data, "transition_id")}}
        return _jira_json_request(input_data, "POST", f"/rest/api/3/issue/{issue_key}/transitions", payload)


class JiraAddAttachmentTool(BaseTool):
    name = "jira_add_attachment"
    description = "Attach an uploaded file to a Jira issue."
    input_schema = {
        "type": "object",
        "required": ["jira_config", "issue_key", "file_id"],
        "properties": {"jira_config": {"type": "object"}, "issue_key": {"type": "string"}, "file_id": {"type": "string"}},
    }

    def execute(self, input_data: dict[str, Any], storage: Storage) -> ToolResult:
        client, _ = _jira_client(input_data)
        meta = storage.get(require_field(input_data, "file_id"))
        try:
            response = client.post(
                f"/rest/api/3/issue/{require_field(input_data, 'issue_key')}/attachments",
                headers={"X-Atlassian-Token": "no-check"},
                files={"file": (meta["filename"], storage.path_for(meta["file_id"]).read_bytes(), meta.get("content_type"))},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ToolExecutionError("jira_request_failed", "Jira attachment upload failed.", {"error": str(exc)}) from exc
        finally:
            client.close()
        return ToolResult(type="json", data=response.json())


def _jira_json_request(
    input_data: dict[str, Any], method: str, path: str, payload: dict[str, Any] | None = None
) -> ToolResult:
    client, _ = _jira_client(input_data)
    try:
        response = client.request(method, path, json=payload)
        response.raise_for_status()
        body = response.json() if response.content else {"success": True}
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise ToolExecutionError("jira_request_failed", "Jira request failed.", {"error": str(exc)}) from exc
    finally:
        client.close()
    return ToolResult(type="json", data=body)
