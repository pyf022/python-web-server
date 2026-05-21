import time
import shutil
from pathlib import Path

from app.core.config import get_settings


def cleanup_expired_files() -> int:
    settings = get_settings()
    cutoff = time.time() - settings.file_ttl_seconds
    removed = 0
    for directory_name in ("uploads", "outputs", "tmp"):
        directory = Path(settings.storage_root) / directory_name
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.stat().st_mtime >= cutoff:
                continue
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
            removed += 1
    return removed
