from app.jobs.tasks import run_tool_job


def test_run_tool_job_direct_success(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    result = run_tool_job("json_yaml_format", {"text": "{\"b\":1,\"a\":2}", "format": "json"})

    assert result["status"] == "succeeded"
    assert result["tool_name"] == "json_yaml_format"
    assert '"a": 2' in result["data"]["formatted"]
