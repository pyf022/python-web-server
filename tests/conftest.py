import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["API_KEYS"] = "test-key"
os.environ["STORAGE_ROOT"] = str(Path("test-data").absolute())

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def headers():
    return {"X-API-Key": "test-key"}
