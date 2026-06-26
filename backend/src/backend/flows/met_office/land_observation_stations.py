import io
from datetime import UTC, datetime
from functools import partial
from typing import Any, Literal

import httpx
import patito as pt
import pendulum
import polars as pl
import polars.selectors as cs
import prefect
from deltalake.exceptions import TableNotFoundError
from prefect.deployments.runner import RunnerDeployment
from pydantic import RootModel
from utils.api.met_office import MetOfficeClientConfig, aget_nearest
from utils.models.met_office import (
    LatLon,
    LatLonFactory,
    MetOfficeLandObservationStationFactory,
    MetOfficeLandObservationStationV1,
)
from utils.storage.client import StorageClientConfig, StorageOptions


class ApiMetadata[I, O](pt.Model):
    service_type: Literal["mock", "live"]
    api_version: Literal["1"] = "1"
    ingested_at: datetime = pt.Field(default_factory=partial(datetime.now, UTC))
    params: I
    data: O

    @staticmethod
    def output_partition(service_type: Literal["mock", "live"]) -> str:
        return f"met_office/land_observation_station/service_type={service_type}"

    @staticmethod
    def output_glob(service_type: Literal["mock", "live"]) -> str:
        return f"met_office/land_observation_station/service_type={service_type}/*.json"

    @property
    def output_file(self):
        return f"{self.output_partition(self.service_type)}/{self.file_name}"

    @property
    def file_name(self):
        return f"{self.ingested_at}_{self.params}_v{self.api_version}.json"


class AwaitingData[I, O](ApiMetadata[I, None]):
    data: None = None

    def with_data(self, data: Any) -> "ApiMetadata[I, O]":
        return ApiMetadata[I, O](
            service_type=self.service_type,
            api_version=self.api_version,
            ingested_at=self.ingested_at,
            params=self.params,
            data=data,
        )


StationParams = AwaitingData[LatLon, MetOfficeLandObservationStationV1]
StationData = ApiMetadata[LatLon, MetOfficeLandObservationStationV1]


@prefect.task(tags=("bronze", "met office", "station"), version="1")
async def fetch_met_office_land_observation_station(
    meta: StationParams,
    client: httpx.AsyncClient,
) -> StationData:
    print(f"fetching data for {meta}")
    response = await aget_nearest(
        client, meta.params.lat, meta.params.lon, version=meta.api_version
    )
    return meta.with_data(await response.aread())


@prefect.task(tags=("bronze", "met office", "station"), version="1")
async def load_met_office_land_observation_station(
    bronze: StorageOptions,
    meta: StationData,
) -> str:
    print(f"loading data for {meta}")
    result = await bronze.client.put_async(
        meta.output_file,
        meta.model_dump_json().encode("utf-8"),
        mode="create",
    )
    print(f"Result of load {result}")
    return meta.output_file


def transform_observations_silver(data: pl.LazyFrame) -> pl.LazyFrame:
    return data.select(cs.exclude(cs.struct()), cs.struct().struct.unnest())


def test_transform_observations_silver():
    data: RootModel[list[StationData]] = RootModel([])

    intervals = pendulum.interval(
        pendulum.datetime(2026, 1, 1), pendulum.datetime(2026, 5, 1)
    )
    for date in intervals.range("months"):
        for batch in MetOfficeLandObservationStationFactory.batch(5):
            data.root.append(
                StationData(
                    service_type="mock",
                    ingested_at=date,
                    params=LatLonFactory.build(),
                    data=batch,
                )
            )
    print(data.model_dump_json().encode("utf8"))
    lf = pl.read_json(
        data.model_dump_json().encode("utf8"),
        schema=StationData.dtypes,
    ).lazy()
    print(lf.collect())
    result = transform_observations_silver(lf).collect()
    print(result)


SILVER_DELTA_WRITE_OPTIONS = {
    "partition_by": ["service_type", "geohash"],
    "schema_mode": "overwrite",
    "configuration": {
        # Target 256MB per Parquet file (value in bytes)
        "delta.targetFileSize": "268435456",
        # Enable deletion vectors to make updates/deletes faster without rewriting whole files
        "delta.enableDeletionVectors": "true",
    },
}
GOLD_DELTA_WRITE_OPTIONS = {
    "partition_by": ["service_type", "run_date"],
    "schema_mode": "overwrite",
    "configuration": {
        # Target 256MB per Parquet file (value in bytes)
        "delta.targetFileSize": "268435456",
    },
}


@prefect.task(tags=("silver", "met office", "station"), version="1")
async def create_observation_station_store(
    bronze: StorageOptions,
    silver: StorageOptions,
    *partitions: str,
) -> None:
    lfs = []
    for path in partitions:
        stream = await bronze.client.get_async(path)
        print(f"transforming bronze data for {path}")
        lf = transform_observations_silver(
            pl.read_json(
                io.BytesIO(stream.buffer()),
                schema=StationData.dtypes,
            ).lazy()
        )
        lfs.append(lf)
    combined_lf = pl.concat(lfs, how="vertical")
    print(f"loading silver data for {len(partitions)} partitions")
    combined_lf.sink_delta(
        "met_office/land_observation_station",
        mode="append",
        storage_options=silver.storage_options,
        delta_write_options=SILVER_DELTA_WRITE_OPTIONS,
    )


@prefect.task(tags=("silver", "met office", "station"), version="1")
async def cleanup_delta_sink(
    silver: StorageOptions,
) -> None:
    try:
        delta = silver.delta_table("met_office/land_observation_station")
    except TableNotFoundError:
        print("Table does not exist yet. Compaction skipped.")
        return
    print("cleaning up silver table partitions")
    (
        pl.scan_delta(delta)
        .sort("ingested_at")
        .sink_delta(
            "met_office/land_observation_station",
            mode="overwrite",
            delta_write_options=SILVER_DELTA_WRITE_OPTIONS,
        )
    )


@prefect.task(tags=("silver", "met office", "station"), version="1")
async def load_latest(
    silver: StorageOptions,
    gold: StorageOptions,
    run_date: datetime,
) -> None:
    delta = silver.delta_table("met_office/land_observation_station")
    lf = (
        pl.scan_delta(delta)
        .sort("ingested_at")
        .unique(["service_type", "geohash"], keep="first", maintain_order=True)
        .with_columns(run_date=pl.date(run_date.year, run_date.month, run_date.day))
    )

    lf.sink_delta(
        "met_office/land_observation_station",
        storage_options=gold.storage_options,
        mode="append",
        delta_write_options=GOLD_DELTA_WRITE_OPTIONS,
    )


@prefect.flow(log_prints=True)
async def met_office_observation_station_pipeline(
    *queries: LatLon,
    run_date: datetime | None = None,
) -> None:
    storage = StorageClientConfig()
    client_model = MetOfficeClientConfig()
    service_type = client_model.met_office.client_type
    base_kwargs: dict[str, Any] = {
        "service_type": service_type,
        "api_version": "1",
    }
    if run_date is not None:
        if service_type != "mock":
            raise Exception(
                f"run date can only be set manually for mock services. found: {service_type}"
            )
        base_kwargs["ingested_at"] = run_date
    else:
        run_date = datetime.now(UTC)

    async with client_model.async_api_client() as client:
        # BRONZE
        bronze_additions = []
        for latlon in queries:
            meta = StationParams(params=latlon, **base_kwargs)
            response = await fetch_met_office_land_observation_station(meta, client)
            bronze_path = await load_met_office_land_observation_station(
                storage.bronze, response
            )
            bronze_additions.append(bronze_path)

        # SILVER
        await create_observation_station_store(
            storage.bronze, storage.silver, *bronze_additions
        )
        await cleanup_delta_sink(storage.silver)

        # GOLD
        await load_latest(storage.silver, storage.gold, run_date)


async def as_deployment(env: Literal["prod", "dev"] = "dev") -> RunnerDeployment:
    return await met_office_observation_station_pipeline.ato_deployment(
        f"met-office-observation-station-pipeline/{env}", version="1"
    )


if __name__ == "__main__":
    test_transform_observations_silver()
