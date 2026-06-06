from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Generator

import httpx
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    SecretStr,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from utils.pydantic_utils import One, Some

MOCK_URL = "http:localhost:8080"
LIVE_URL = "https://datahub.metoffice.gov.uk"


class _GlobalSettings(BaseSettings):
    """Private config model.

    use met_office_client_factory() to instantiate this model.

    provides utilities to create a httpx.client for the service.

    Servic can either be the mock service, or live api.
    """

    model_config = SettingsConfigDict(
        env_file=".env",  # Reads from a local .env file if present. register an application to use
        env_file_encoding="utf-8",
        extra="ignore",
    )
    use_mock_services: bool = Field(False, validation_alias="USE_MOCK_SERVICES")


class _MetOfficeClientConfig(BaseSettings):
    """Private config model.

    use met_office_client_factory() to instantiate this model.

    provides utilities to create a httpx.client for the service.

    Servic can either be the mock service, or live api.
    """

    model_config = SettingsConfigDict(
        env_file=".env",  # Reads from a local .env file if present. register an application to use
        env_file_encoding="utf-8",
        extra="ignore",
    )
    secret: SecretStr = Field(..., validation_alias="MET_OFFICE_CLIENT_SECRET")
    base_url: HttpUrl = Field(
        LIVE_URL, validation_alias="MET_OFFICE_BASE_URL", validate_default=True
    )

    def _authenticate_request(self, request: httpx.Request) -> httpx.Request:
        """Private auth flow method."""
        request.headers["apikey"] = self.secret.get_secret_value()
        return request

    @asynccontextmanager
    async def async_api_client(self) -> AsyncGenerator[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            base_url=self.base_url.encoded_string(),
            auth=self._authenticate_request,
            headers={
                "accept": "application/json",
            },
        ) as session:
            yield session

    @contextmanager
    def api_client(self) -> Generator[httpx.Client]:
        with httpx.Client(
            base_url=self.base_url.encoded_string(),
            auth=self._authenticate_request,
            headers={
                "accept": "application/json",
            },
        ) as session:
            yield session


def met_office_client_factory(use_mock: bool | None = None) -> _MetOfficeClientConfig:
    if use_mock is None:
        use_mock = _GlobalSettings().use_mock_services
    if use_mock:
        return _MetOfficeClientConfig.model_construct(
            met_office_base_url=MOCK_URL, met_office_client_secret="apikey"
        )
    return _MetOfficeClientConfig()


class MetOfficeLandObservationNearest(BaseModel):
    """/observation-land/1/nearest"""

    geohash: str
    """Geohash of the observation location"""
    area: str
    """Location area"""
    region: str | None
    """Region code for UK locations"""
    country: str | None
    """The country of the location"""
    olson_time_zone: str | None
    """Olson time zone string of location"""


class MetOfficeLandObservationGeohash(BaseModel):
    """/observation-land/1/{geohash}"""

    datetime: datetime
    """Date of the observation."""
    humidity: int | None
    """Probability as a percentage of 100."""
    mslp: int | None
    """Mean surface level pressure in hPA."""
    pressure_tendency: str | None
    """Pressure tendency representing Rising, Falling or Steady."""
    temperature: float | None
    """Air temperature in °C."""
    visibility: int | None
    """Visibility in metres."""
    weather_code: int | None
    """Numerical code for the weather symbol."""
    wind_direction: str | None
    """Direction the wind is travelling from in 16 point compass notation."""
    wind_gust: float | None
    """Wind gust speed in m/s."""
    wind_speed: float | None
    """Wind speed in m/s."""


async def get_observation_async(
    client_session: httpx.AsyncClient, geohash: str
) -> bytes:
    response = await client_session.get(f"/observation-land/1/{geohash}")
    response.raise_for_status()
    return response.content


def get_observation(client_session: httpx.Client, geohash: str) -> bytes:
    response = client_session.get(f"/observation-land/1/{geohash}")
    response.raise_for_status()
    return response.content


def get_nearest(
    client: httpx.Client,
    lat: float,
    lon: float,
) -> bytes:
    params = {"lat": lat, "lon": lon}
    response = client.get("/observation-land/1/nearest", params=params)
    response.raise_for_status()
    return response.content


if __name__ == "__main__":
    cfg = met_office_client_factory()
    with cfg.api_client() as client:
        nearest = (
            One[MetOfficeLandObservationNearest]
            .model_validate_json(get_nearest(client, 50.72, -3.53))
            .item
        )
        observation = (
            Some[MetOfficeLandObservationGeohash]
            .model_validate_json(get_observation(client, nearest.geohash))
            .root
        )
        print(observation, len(observation))
