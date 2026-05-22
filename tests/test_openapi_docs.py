def test_convert_download_openapi_documents_parameters(client, headers):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    operation = spec["paths"]["/v1/convert/download"]["post"]
    body_ref = operation["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    schema_name = body_ref.rsplit("/", 1)[-1]
    body_schema = spec["components"]["schemas"][schema_name]

    assert "一步上传转换并下载结果文件" == operation["summary"]
    assert "md_to_word" in operation["description"]
    assert "pdf_to_word" in operation["description"]
    assert "tool_name" in body_schema["properties"]
    assert "适合直接下载文件流" in body_schema["properties"]["tool_name"]["description"]
    assert "extra_input" in body_schema["properties"]
    assert "JSON 字符串" in body_schema["properties"]["extra_input"]["description"]
    assert "output_filename" in body_schema["properties"]
    assert "输出文件名" in body_schema["properties"]["output_filename"]["description"]


def test_tool_schemas_have_human_readable_descriptions(client, headers):
    response = client.get("/v1/tools", headers=headers)

    assert response.status_code == 200
    tools = {tool["name"]: tool for tool in response.json()["tools"]}
    assert "md_to_word" in tools
    assert "pdf_to_word" in tools
    assert "word_to_pdf" in tools
    assert "description" in tools["md_to_word"]["input_schema"]["properties"]["file_id"]
    assert "examples" in tools["pdf_to_word"]["input_schema"]["properties"]["file_id"]
    assert tools["json_yaml_format"]["input_schema"]["properties"]["format"]["enum"] == ["json", "yaml"]
