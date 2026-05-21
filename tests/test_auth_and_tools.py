def test_requires_api_key(client):
    response = client.get("/v1/tools")
    assert response.status_code == 401


def test_lists_builtin_tools(client, headers):
    response = client.get("/v1/tools", headers=headers)
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    assert "md_to_pdf" in names
    assert "json_yaml_format" in names
    assert "word_to_pdf" in names


def test_json_yaml_format_sync(client, headers):
    response = client.post(
        "/v1/tools/json_yaml_format/run",
        headers=headers,
        json={"input": {"text": "{\"b\":1,\"a\":2}", "format": "json"}},
    )
    assert response.status_code == 200
    formatted = response.json()["result"]["data"]["formatted"]
    assert '"a": 2' in formatted
    assert '"b": 1' in formatted
