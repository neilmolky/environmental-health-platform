import os
import pathlib

import pytest

from backend.storage.client import get_storage_client


def test_local_filesystem_smoke_pass(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Asserts that the storage factory can fall back to a local file system cleanly.

    Verifies read and write operations inside an isolated temporary directory.
    """
    # 1. Force the factory to use the local filesystem driver
    monkeypatch.setenv("STORAGE_BACKEND", "file")

    # 2. Resolve the client using your actual factory function
    fs = get_storage_client()

    # 3. Establish temporary paths inside the sandboxed pytest directory
    bucket_name = str(tmp_path / "environmental-health-lake")
    target_path = f"{bucket_name}/raw_weather/v1/smoke_test.txt"
    test_data = b"Factory Verification - Local File System Stream Functioning"

    parent_dir = os.path.dirname(target_path)
    fs.makedirs(parent_dir, exist_ok=True)

    with fs.open(target_path, "wb") as f:
        f.write(test_data)

    retrieved_data = fs.cat_file(target_path)

    # 5. Assert structural consistency
    assert retrieved_data == test_data
