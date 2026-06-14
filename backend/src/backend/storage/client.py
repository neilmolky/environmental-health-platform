"""Cloud-agnostic storage abstraction layer supporting AWS S3 and Azure Blob."""

import os

import fsspec


def get_storage_client() -> fsspec.AbstractFileSystem:
    """
    Return an fsspec filesystem client configured according to the STORAGE_BACKEND
    environment variable.

    Supported backends:
    - "aws": returns an S3 filesystem configured from
             AWS_ENDPOINT_URL,
             AWS_ACCESS_KEY_ID,
             AWS_SECRET_ACCESS_KEY.
    - "azure": returns an ABFS filesystem configured from:
               AZURE_STORAGE_CONNECTION_STRING.
    - "file": returns a local filesystem.

    Returns:
        fsspec.AbstractFileSystem: A filesystem client instance configured for the
        selected backend.

    Raises:
        NotImplementedError: If STORAGE_BACKEND is set to an unsupported value.
    """
    backend_type = os.getenv("STORAGE_BACKEND", "file").lower()

    match backend_type:
        case "aws":
            # Point explicitly to the local MinIO container configured in Compose
            return fsspec.filesystem(
                "s3",
                client_kwargs={"endpoint_url": os.getenv("AWS_ENDPOINT_URL")},
                key=os.getenv("AWS_ACCESS_KEY_ID"),
                secret=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )

        case "azure":
            # Point explicitly to the local Azurite container connection string
            return fsspec.filesystem(
                "abfs",
                connection_string=os.getenv(
                    "AZURE_STORAGE_CONNECTION_STRING",
                ),
            )
        case "file":
            # generally used for local testing
            return fsspec.filesystem("file")

        case other:
            raise NotImplementedError(f"STORAGE_BACKEND: {other} is not implemented")
