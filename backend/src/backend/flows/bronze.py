from datetime import UTC, datetime
from functools import partial
from typing import Any, Literal

import fsspec
import httpx
import prefect
from pydantic import BaseModel, Field, model_validator

from backend.bronze.met_office.client import (
    MetOfficeClientConfig,
    get_observation_async,
)
from backend.bronze.met_office.register_geohash import MetOfficeLandObservationRegistry
from backend.storage.client import get_storage_client


class _MetOfficeBronzeMetadataMock(BaseModel):
    service_type: Literal["mock"]
    api_version: str = Field(pattern="\d+")
    geohash: str
    ingested_at: datetime = Field(default_factory=partial(datetime.now, UTC))


class _MetOfficeBronzeMetadataLive(BaseModel):
    service_type: Literal["live"]
    api_version: str = Field(pattern="\d+")
    geohash: str
    ingested_at: datetime = Field(default_factory=partial(datetime.now, UTC))

    @model_validator(mode="before")
    @classmethod
    def reject_user_ingested_at(cls, data: Any) -> Any:
        # Check if 'ingested_at' was explicitly provided by the user
        if isinstance(data, dict) and "ingested_at" in data:
            raise ValueError(
                "The 'ingested_at' field is managed automatically and cannot be provided manually."
            )
        return data


class MetOfficeBronzeMetadata(BaseModel):
    meta: _MetOfficeBronzeMetadataLive | _MetOfficeBronzeMetadataMock = Field(
        discriminator="service_type"
    )

    @property
    def partition_scheme(self):
        return "service_type={}/api_version={}/geogash={}/ingested_at={}".format(
            self.meta.service_type,
            self.meta.api_version,
            self.meta.geohash,
            self.meta.ingested_at,
        )

    @classmethod
    def from_partition_scheme(cls, partition_scheme: str) -> "MetOfficeBronzeMetadata":
        expected_model = {
            k: v
            for partition in partition_scheme.split("/")
            for k, v in partition.split("=")
        }
        return cls.model_validate({"meta": expected_model}, extra="forbid")

    @classmethod
    def file_name(self):
        return "data.json"

    @classmethod
    def output_root(self):
        return "bronze/met_office/land_observation"

    @property
    def output_file(self):
        return f"{self.output_root()}/{self.partition_scheme}/{self.file_name()}"

    @classmethod
    def from_path(cls, path: str) -> "MetOfficeBronzeMetadata":
        partition_scheme = path.removeprefix(cls.output_root()).removesuffix(
            cls.file_name()
        )
        return cls.from_partition_scheme(partition_scheme)


@prefect.task(log_prints=True)
async def ingest_met_office_land_observation(
    client: httpx.AsyncClient,
    fs: fsspec.AbstractFileSystem,
    *,
    metadata: MetOfficeBronzeMetadata,
) -> None:
    print(f"loading met office land observations for {metadata.partition_scheme}")
    stream = await get_observation_async(client, metadata.meta.geohash)

    print(f"writing to {metadata.output_file}")
    fs.write_bytes(metadata.output_file, stream)
    print(f"success writing {metadata.output_file}")


@prefect.flow
async def run_met_office_bronze_pipeline(
    ingestion_date: datetime | None = None, api_version: str = "1"
) -> None:
    fs = get_storage_client()
    client_model = MetOfficeClientConfig()
    registry = MetOfficeLandObservationRegistry.load_from_disk()
    async with client_model.async_api_client() as client:
        for geohash in registry.get_geohash_set():
            meta = {
                "geohash": geohash,
                "service_type": client_model.met_office.client_type,
                "api_version": api_version,
            }
            if ingestion_date:
                meta["ingested_at"] = str(ingestion_date)

            await ingest_met_office_land_observation(
                client, fs, metadata=MetOfficeBronzeMetadata.model_validate(meta)
            )
