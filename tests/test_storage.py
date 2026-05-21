from fastapi import UploadFile

from app.storage.local import LocalStorage


def test_local_storage_save_and_get(tmp_path):
    storage = LocalStorage(tmp_path)
    stored = storage.save_bytes(b"hello", "hello.txt", "text/plain")

    assert stored["file_id"].endswith(".txt")
    loaded = storage.get(stored["file_id"])
    assert loaded["filename"] == "hello.txt"
    assert storage.path_for(stored["file_id"]).read_bytes() == b"hello"
