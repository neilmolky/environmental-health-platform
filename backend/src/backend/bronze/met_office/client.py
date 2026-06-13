import os
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

import httpx
from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from utils.met_office_models import (
    LatLon,
    MetOfficeLandObservation,
    MetOfficeLandObservationStation,
)
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
        env_file=".env",  # Reads from a local .env file if present.
        env_file_encoding="utf-8",
        extra="ignore",
    )
    secret: SecretStr = Field(..., validation_alias="MET_OFFICE_CLIENT_SECRET")
    base_url: HttpUrl = Field(
        MET_OFFICE_LIVE_URL,
        validation_alias="MET_OFFICE_URL",
        validate_default=True,
    )

    def add_auth_header(self, request: httpx.Request) -> httpx.Request:
        """
        Attach the configured API key to the given HTTPX request's headers.

        Parameters:
            request (httpx.Request): The outgoing HTTP request to modify.

        Returns:
            httpx.Request: The same request instance with its "apikey" header set.
        """
        request.headers["apikey"] = self.secret.get_secret_value()
        return request

    @asynccontextmanager
    async def async_api_client(self) -> AsyncGenerator[httpx.AsyncClient]:
        """
        Provide an HTTPX async client preconfigured for Met Office requests.

        Returns:
            httpx.AsyncClient: An async HTTP client with `base_url` set to the
            configured Met Office URL, a per-request `apikey` header injected
            from the client's secret, and `Accept: application/json` set.
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
        Create a synchronous HTTP client configured for the Met Office API.

        The client injects the API key via the `apikey` header on each request
        and sets `Accept: application/json`.

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


# TODO: consider redesign of context switching.
# Pydantic settings discourages using model_construct in this way
def met_office_client_factory(use_mock: bool | None = None) -> _MetOfficeClientConfig:
    """
    Produce a _MetOfficeClientConfig configured for mock or live Met Office API access.
    
    If `use_mock` is None, selection is based on whether the environment variable `MET_OFFICE_URL` is present. When `use_mock` is True, the returned config is primed for testing with a fixed client secret. When False, the returned config is set up for the live Met Office service using the module's live base URL.
    
    Parameters:
        use_mock: When True, return a config populated with a fixed mock secret. When False, return a config populated for live use. When None, select mode based on presence of `MET_OFFICE_URL` in the environment.
    
    Returns:
        _MetOfficeClientConfig: A configured client settings object ready for creating HTTP clients.
    """
    if use_mock is None:
        use_mock = os.getenv("MET_OFFICE_URL") is not None
    if use_mock:
        return _MetOfficeClientConfig.model_validate(
            {"MET_OFFICE_CLIENT_SECRET": "apikey"}
        )
    return _MetOfficeClientConfig.model_validate(
        {"MET_OFFICE_URL": MET_OFFICE_LIVE_URL}
    )


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
    params = LatLon.model_validate({"lat": lat, "lon": lon})
    response = client.get("/observation-land/1/nearest", params=params.model_dump())
    response.raise_for_status()
    return response.content


if __name__ == "__main__":
    cfg = met_office_client_factory()
    with cfg.api_client() as client:
        nearest = (
            One[MetOfficeLandObservationStation]
            .model_validate_json(get_nearest(client, 50.72, -3.53))
            .item
        )
        observation = (
            Some[MetOfficeLandObservation]
            .model_validate_json(get_observation(client, nearest.geohash))
            .root
        )
        print(observation, len(observation))
