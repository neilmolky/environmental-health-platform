"""Cloud-agnostic storage abstraction layer supporting AWS S3 and Azure Blob."""

from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal, Self, assert_never

from deltalake import DeltaTable
from obstore.store import AzureStore, ObjectStore, S3Store
from pydantic import BaseModel, Field

from utils.api.base_client import ClientModel


class AwsStorageConfig(BaseModel):
    backend: Literal["aws"]

    def store(self, medalion_layer: Literal["bronze", "silver", "gold"]) -> ObjectStore:
        """see obstore documentation"""
        return S3Store(bucket=medalion_layer)


class AzureStorageConfig(BaseModel):
    backend: Literal["azure"]

    def store(self, medalion_layer: Literal["bronze", "silver", "gold"]) -> ObjectStore:
        """We lose some of the features of azure blob storage by seeking a generic
        implementation because containers are a sub-unit to the Storage Account parent.

        This highlights the risks of a generic implementation.

        For Azure, this strategy is not optimized."""
        return AzureStore(container_name=medalion_layer)


@dataclass(frozen=True)
class StorageOptions:
    medalion_layer: Literal["bronze", "silver", "gold"]
    cfg: AwsStorageConfig | AzureStorageConfig

    @cached_property
    def client(self) -> ObjectStore:
        return self.cfg.store(self.medalion_layer)

    @cached_property
    def storage_options(self) -> dict[str, Any]:
        """
        Utility method for zero-overhead Polars read and write sessions.
        """
        return {"filesystem": self.client.as_fsspec()}

    @property
    def prefix(self) -> str:
        match self.cfg.backend:
            case "aws":
                return f"s3://{self.medalion_layer}"
            case "azure":
                return f"azfs://{self.medalion_layer}"
            case _:
                assert_never()

    @classmethod
    def from_cfg(
        cls,
        cfg: AwsStorageConfig | AzureStorageConfig,
        medalion_layer: Literal["bronze", "silver", "gold"],
    ) -> Self:
        return cls(medalion_layer, cfg)

    def delta_table(self, path: str) -> DeltaTable:
        return DeltaTable(
            path,
            storage_options=self.storage_options,
        )


class StorageClientConfig(ClientModel):
    storage: AwsStorageConfig | AzureStorageConfig = Field(
        default_factory=dict, discriminator="backend"
    )

    @cached_property
    def bronze(self) -> StorageOptions:
        return StorageOptions.from_cfg(self.storage, "bronze")

    @cached_property
    def silver(self) -> StorageOptions:
        return StorageOptions.from_cfg(self.storage, "silver")

    @cached_property
    def gold(self) -> StorageOptions:
        return StorageOptions.from_cfg(self.storage, "gold")
