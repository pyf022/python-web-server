from fastapi import Depends, Header, HTTPException, status
from redis import Redis
from rq import Queue

from app.core.config import Settings, get_settings
from app.storage.local import LocalStorage
from app.storage.base import Storage


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_api_key or x_api_key not in settings.api_key_set:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing or invalid X-API-Key."},
        )


def get_storage(settings: Settings = Depends(get_settings)) -> Storage:
    return LocalStorage(settings.storage_root)


def get_queue(settings: Settings = Depends(get_settings)) -> Queue:
    redis = Redis.from_url(settings.redis_url)
    return Queue("tool-jobs", connection=redis, default_timeout=settings.job_timeout_seconds)
