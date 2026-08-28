"""Cloud-agnostic storage abstraction layer supporting AWS S3 and Azure Blob."""

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated, Literal, Self, assert_never

import patito as pt
from deltalake import DeltaTable
from narwhals.schema import Schema
from obstore.store import AzureStore, ObjectStore, S3Store
from pydantic import BaseModel, Field

from utils.api.base_client import ClientModel

BUCKET_SAFE_PATTERN = r"^[a-zA-Z0-9\-_./=]+$"

# Define the custom type alias
BucketSafeString = Annotated[
    str,
    Field(
        pattern=BUCKET_SAFE_PATTERN,
        description="A URL-safe directory string",
    ),
]


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

    def uri(self, path: str) -> str:
        return f"{self.prefix}/{path}"

    def delta_table(self, path: str) -> DeltaTable:
        return DeltaTable(self.uri(path))

    def create_delta_table(
        self,
        path: str,
        model: type[pt.Model],
        partition_by: list[str] | str | None = None,
        name: str | None = None,
        description: str | None = None,
        configuration: Mapping[str, str | None] | None = None,
    ) -> DeltaTable:
        return DeltaTable.create(
            table_uri=self.uri(path),
            schema=Schema.from_polars(model.dtypes).to_arrow(),
            mode="ignore",
            partition_by=partition_by,
            name=name,
            description=description,
            configuration=configuration,
        )

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


# if __name__ == "__main__":
#     import patito as pt
#     import polars as pl
#     from narwhals.schema import Schema

#     class TestData(pt.Model, frozen=True):
#         foo: str
#         bar: str

#     silver = StorageClientConfig().silver

#     dt = DeltaTable.create(
#         table_uri=silver.uri("test"),
#         schema=Schema.from_polars(TestData.dtypes).to_arrow(),
#         partition_by="bar",
#         mode="ignore",
#     )
#     print(
#         TestData.DataFrame({"foo": ["test"], "bar": ["test"]})
#         .lazy()
#         .sink_delta(silver.uri("test"), mode="append")
#     )
#     print(pl.read_delta(silver.uri("test")))
