from datetime import UTC, datetime
from typing import Any, Literal, overload

import anyio
import httpx
import patito as pt
import pendulum
import polars as pl
import polars.selectors as cs
import prefect
from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError
from prefect.cache_policies import NO_CACHE
from prefect.deployments.runner import RunnerDeployment
from prefect.logging import get_run_logger
from pydantic import RootModel
from utils.api.base_client import ApiMetadata, AwaitingData
from utils.api.met_office import MetOfficeClientConfig, aget_observation
from utils.models.met_office import (
    GeoHash,
    LatLonFactory,
    MetOfficeLandObservationV1,
    MetOfficeLandObservationV1Factory,
)
from utils.storage.client import StorageClientConfig, StorageOptions

ObsParams = AwaitingData[GeoHash, list[MetOfficeLandObservationV1]]
ObsData = ApiMetadata[GeoHash, list[MetOfficeLandObservationV1]]


class LatestValidStations(RootModel[list[GeoHash]]):
    pass


@prefect.task(
    tags=("bronze", "met office", "observation"),
    version="1",
    cache_policy=NO_CACHE,
)
async def get_current_stations(
    gold: StorageOptions,
    service_type: Literal["mock", "live"],
) -> LatestValidStations:
    delta = gold.delta_table("met_office/land_observation_station")
    return LatestValidStations.model_validate(
        pl.scan_delta(delta)
        .filter(run_date=pl.max("run_date"), service_type=service_type)
        .select("geohash")
        .collect()
        .to_dicts()
    )


@prefect.task(
    tags=("bronze", "met office", "observation"),
    version="1",
    cache_policy=NO_CACHE,
)
async def fetch_land_observation(
    client: httpx.AsyncClient,
    station: ObsParams,
) -> ObsData:
    if station.api_version != "1":
        raise ValueError(f"api version {station.api_version} not supported")
    try:
        response = await aget_observation(
            client, station.params, version=station.api_version
        )
    except:
        print(f"client failed to connect to : {client.base_url}")
        raise
    return station.with_data(await response.aread())


@prefect.task(
    tags=("bronze", "met office", "station"), version="1", cache_policy=NO_CACHE
)
async def load_land_observation(
    bronze: StorageOptions,
    data: ObsData,
) -> str:
    file_path = (
        "met_office/land_observation/"
        f"{data.service_type}_data/"
        f"{data.ingested_at:%Y%m%d_%H%m%S}/"
        f"{data.params}_v{data.api_version}.json"
    )
    print(f"loading data {data}")

    result = await bronze.client.put_async(
        file_path,
        data.model_dump_json().encode("utf-8"),
        mode="create",
    )
    print(f"Result of load {result}")
    return file_path


SILVER_PARTITION = ["service_type", "geohash"]
GOLD_PARTITION = ["service_type", "year", "month"]


class SilverSchema(pt.Model, frozen=True):
    api_version: str
    ingested_at: datetime
    service_type: str
    geohash: str
    observation_date: datetime = pt.Field(alias="datetime")
    humidity: int | None
    mslp: int | None
    pressure_tendency: str | None
    temperature: float | None
    visibility: int | None
    weather_code: int | None
    wind_direction: str | None
    wind_gust: float | None
    wind_speed: float | None
    year: int
    month: int
    day: int
    hour: int


class GoldSchema(SilverSchema, frozen=True):
    run_date: datetime


def create_silver_table(silver: StorageOptions) -> DeltaTable:
    return silver.create_delta_table(
        "met_office/land_observation",
        SilverSchema,
        partition_by=SILVER_PARTITION,
        configuration={
            "delta.targetFileSize": "268435456",
        },
    )


def create_gold_table(gold: StorageOptions) -> DeltaTable:
    return gold.create_delta_table(
        "met_office/land_observation",
        GoldSchema,
        partition_by=GOLD_PARTITION,
        name="met_office_land_observation",
        configuration={
            "delta.targetFileSize": "268435456",
        },
    )


@overload
def transform_observations_silver(data: pl.DataFrame) -> pl.DataFrame: ...


@overload
def transform_observations_silver(data: pl.LazyFrame) -> pl.LazyFrame: ...


def transform_observations_silver(
    data: pl.DataFrame | pl.LazyFrame,
) -> pl.DataFrame | pl.LazyFrame:
    observation_date = pl.col("datetime")
    return (
        data.explode(cs.list())
        .select(cs.exclude(cs.struct()), cs.struct().struct.unnest())
        .with_columns(
            observation_date=observation_date,
            year=observation_date.dt.year(),
            month=observation_date.dt.month(),
            day=observation_date.dt.day(),
            hour=observation_date.dt.hour(),
        )
        .select(cs.exclude(*SILVER_PARTITION, "datetime"), *SILVER_PARTITION)
    )


def test_transform_observations_silver():
    data: RootModel[list[ObsData]] = RootModel([])

    intervals = pendulum.interval(
        pendulum.datetime(2026, 1, 1), pendulum.datetime(2026, 5, 1)
    )
    for date in intervals.range("months"):
        for batch in MetOfficeLandObservationV1Factory.batch(24):
            data.root.append(
                ObsData(
                    service_type="mock",
                    ingested_at=date,
                    params=LatLonFactory.build().calculate_geohash(),
                    data=[batch],
                )
            )
    print(data.model_dump_json().encode("utf8"))
    lf = pl.read_json(
        data.model_dump_json().encode("utf8"),
        schema_overrides=ObsData.dtypes,
    ).lazy()
    print(lf.collect())
    result = transform_observations_silver(lf).collect()
    print(result)


@prefect.task(
    tags=("silver", "met office", "station"), version="1", cache_policy=NO_CACHE
)
async def create_observation_station_store(
    bronze: StorageOptions,
    silver: StorageOptions,
    *ingests: str,
) -> None:
    lfs = []
    for path in ingests:
        print(f"transforming bronze data for {path}")
        lf = transform_observations_silver(
            pl.scan_ndjson(
                bronze.uri(path),
                schema=ObsData.dtypes,
            )
        )
        lfs.append(lf)
    combined_lf = pl.concat(lfs, how="vertical")
    print(f"loading silver data for {len(ingests)} ingests")

    delta_table = create_silver_table(silver)
    combined_lf.sink_delta(
        delta_table,
        mode="append",
    )


@prefect.task(
    tags=("silver", "met office", "station"), version="1", cache_policy=NO_CACHE
)
async def cleanup_delta_sink(
    silver: StorageOptions,
) -> None:
    try:
        delta = silver.delta_table("met_office/land_observation")
    except TableNotFoundError:
        print("Table does not exist yet. Compaction skipped.")
        return
    print("cleaning up silver table partitions")
    (
        pl.scan_delta(delta)
        .sort("observation_date", "ingested_at")
        .sink_delta(
            delta,
            mode="overwrite",
        )
    )


@prefect.task(
    tags=("silver", "met office", "station"), version="1", cache_policy=NO_CACHE
)
async def load_latest(
    silver: StorageOptions,
    gold: StorageOptions,
    run_date: datetime,
) -> None:
    delta = silver.delta_table("met_office/land_observation")
    lf = (
        pl.scan_delta(delta)
        .sort("observation_date", "ingested_at")
        .unique(
            [*SILVER_PARTITION, "observation_date"], keep="first", maintain_order=True
        )
        .with_columns(run_date=pl.lit(run_date))
        .select(
            cs.exclude(*GOLD_PARTITION),
            *GOLD_PARTITION,
        )
    )

    final_table = create_gold_table(gold)
    lf.sink_delta(
        final_table,
        mode="append",
    )


@prefect.flow(log_prints=True)
async def met_office_observation_pipeline(
    run_date: datetime | None = None,
) -> None:
    storage = StorageClientConfig()
    client_model = MetOfficeClientConfig()
    logger = get_run_logger()
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
        current_stations = await get_current_stations(storage.gold, service_type)
        print(current_stations)
        for geohash in current_stations.root:
            meta = ObsParams(params=geohash, **base_kwargs)
            try:
                response = await fetch_land_observation(client, meta)
                bronze_path = await load_land_observation(storage.bronze, response)
                bronze_additions.append(bronze_path)
            except httpx.HTTPStatusError as e:
                logger.error(e)

        # SILVER
        await create_observation_station_store(
            storage.bronze, storage.silver, *bronze_additions
        )
        await cleanup_delta_sink(storage.silver)

        # GOLD
        await load_latest(storage.silver, storage.gold, run_date)


async def as_deployment(env: Literal["prod", "dev"] = "dev") -> RunnerDeployment:
    return await met_office_observation_pipeline.ato_deployment(env, version="1")


if __name__ == "__main__":
    anyio.run(met_office_observation_pipeline)
