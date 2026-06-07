import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Generator

import httpx
from pydantic import BaseModel, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from utils.pydantic_utils import One, Some

MET_OFFICE_LIVE_URL = "https://data.hub.api.metoffice.gov.uk"
MET_OFFICE_USER_URL = "https://datahub.metoffice.gov.uk"


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
        MET_OFFICE_LIVE_URL,
        validation_alias="MET_OFFICE_MOCK_URL",
        validate_default=True,
    )

    def add_auth_header(self, request: httpx.Request) -> httpx.Request:
        """
        Attach the configured API key to the provided HTTPX request's headers.

        Parameters:
            request (httpx.Request): The outgoing HTTP request to modify.

        Returns:
            httpx.Request: The same request instance with its "apikey" header set to the configured secret.
        """
        request.headers["apikey"] = self.secret.get_secret_value()
        return request

    @asynccontextmanager
    async def async_api_client(self) -> AsyncGenerator[httpx.AsyncClient]:
        """
        Create an async context manager that yields an httpx.AsyncClient configured with the Met Office base URL and API key header.

        Returns:
            httpx.AsyncClient: A configured HTTPX async client instance.
        """
        async with httpx.AsyncClient(
            base_url=self.base_url.encoded_string(),
            auth=self.add_auth_header,
            headers={
                "accept": "application/json",
            },
        ) as session:
            yield session

    @contextmanager
    def api_client(self) -> Generator[httpx.Client]:
        """
        Provide a synchronous HTTP client configured for the Met Office API as a context manager.

        The client uses this config's `base_url`, injects the API key via the `apikey` header on each request, and sets `Accept: application/json`. The client is automatically closed when the context manager exits.

        Returns:
            httpx.Client: A configured synchronous HTTP client instance.
        """
        with httpx.Client(
            base_url=self.base_url.encoded_string(),
            auth=self.add_auth_header,
            headers={
                "accept": "application/json",
            },
        ) as session:
            yield session


def met_office_client_factory(use_mock: bool | None = None) -> _MetOfficeClientConfig:
    """
    Create a configured Met Office client config for mock or live use.

    Parameters:
        use_mock (bool | None): When True, return a config primed for mock usage. When False, return a config populated from environment/.env. When None (default), decide based on presence of the `MET_OFFICE_MOCK_URL` environment variable.

    Returns:
        _MetOfficeClientConfig: A configured client object. If `use_mock` is True, the returned config is populated with a fixed secret value for mocking; otherwise it is populated from environment/.env.
    """
    if use_mock is None:
        use_mock = os.getenv("MET_OFFICE_MOCK_URL") is not None
    if use_mock:
        return _MetOfficeClientConfig.model_validate(
            {"MET_OFFICE_CLIENT_SECRET": "apikey"}
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
    """
    Retrieve the raw response body for a land observation identified by `geohash`.

    Parameters:
        geohash (str): Geohash identifying the observation location.

    Returns:
        bytes: Response body bytes containing the observation payload.

    Raises:
        httpx.HTTPStatusError: If the HTTP response status is not 2xx.
    """
    response = await client_session.get(f"/observation-land/1/{geohash}")
    response.raise_for_status()
    return response.content


def get_observation(client_session: httpx.Client, geohash: str) -> bytes:
    """
    Fetches land observation data for the given geohash from the Met Office API.

    Parameters:
        geohash (str): Geohash identifying the observation location.

    Returns:
        bytes: Raw response body (JSON) returned by the API.
    """
    response = client_session.get(f"/observation-land/1/{geohash}")
    response.raise_for_status()
    return response.content


def get_nearest(
    client: httpx.Client,
    lat: float,
    lon: float,
) -> bytes:
    """
    Fetch the nearest land observation for the specified geographic coordinates.

    Parameters:
        lat (float): Latitude in decimal degrees.
        lon (float): Longitude in decimal degrees.

    Returns:
        bytes: Raw response body bytes containing the nearest observation JSON.

    Raises:
        httpx.HTTPStatusError: If the HTTP response status is not 2xx.
    """
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
