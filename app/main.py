from fastapi import FastAPI

from app.api.routes import convert, files, jobs, process, tools
from app.core.config import get_settings
from app.tools.registry import register_builtin_tools

settings = get_settings()
register_builtin_tools()

app = FastAPI(
    title="Python AI Tool Server",
    version="0.1.0",
    description="Unified API gateway for AI agent utilities and third-party system integrations.",
)

app.include_router(files.router, prefix="/v1")
app.include_router(tools.router, prefix="/v1")
app.include_router(jobs.router, prefix="/v1")
app.include_router(convert.router, prefix="/v1")
app.include_router(process.router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
