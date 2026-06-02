"""Cloud-agnostic storage abstraction layer supporting AWS S3 and Azure Blob."""

import os

import fsspec


def get_storage_client() -> fsspec.AbstractFileSystem:
    """Factory function resolving the client based on runtime environment."""
    backend_type = os.getenv("STORAGE_BACKEND", "aws").lower()

    match backend_type:
        case "aws":
            # Point explicitly to the local MinIO container endpoint configured in Compose
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

        case other:
            raise NotImplementedError(f"STORAGE_BACKEND: {other} is not implemented")
