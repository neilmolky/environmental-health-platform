"""Integration tests verifying native fsspec file operations across cloud profiles."""

import pytest

from backend.storage import get_storage_client


@pytest.mark.parametrize("backend_profile", ["aws", "azure"])
def test_storage_lifecycle_across_profiles(
    backend_profile: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Asserts that the fsspec factory initializes, writes, and reads back data successfully.

    Dynamically tests both AWS (MinIO) and Azure (Azurite) configurations using monkeypatch.
    """
    # 1. Force the factory function to target the current parameterised backend profile
    monkeypatch.setenv("STORAGE_BACKEND", backend_profile)

    # 2. Instantiate the corresponding fsspec filesystem client
    fs = get_storage_client()

    bucket_name = "test-environmental-bucket"
    target_path = f"{bucket_name}/raw_weather/v1/test_metric_{backend_profile}.txt"
    test_data = f"Simulated payload for {backend_profile} cluster stream".encode(
        "utf-8"
    )

    # 3. Create the target bucket/container directory if missing
    if not fs.exists(bucket_name):
        fs.mkdir(bucket_name)

    # 4. Write data stream natively using context management
    with fs.open(target_path, "wb") as f:
        f.write(test_data)

    # 5. Read data bytes instantly back from the emulator memory
    retrieved_data = fs.cat_file(target_path)

    # 6. Validate structural data consistency
    assert retrieved_data == test_data

    # Cleanup test artifact to preserve pristine storage state
    fs.rm(target_path)
