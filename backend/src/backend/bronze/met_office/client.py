from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Literal

import httpx
from pydantic import BaseModel, Field, HttpUrl, SecretStr
from utils.met_office_models import (
    LatLon,
    MetOfficeLandObservationStation,
    MetOfficeLandObservationV1,
)
from utils.pydantic_utils import One, Some

from backend.bronze.base_client import ClientModel

MET_OFFICE_LIVE_URL = "https://data.hub.api.metoffice.gov.uk"
MET_OFFICE_USER_URL = "https://datahub.metoffice.gov.uk"


class _MetOfficeClientConfigMock(BaseModel):
    client_type: Literal["mock"]

    base_url: HttpUrl = Field(
        ...,
        validation_alias="mock_url",
        description="The base_url is required for mock service as the user must spin the service up.",
    )
    secret: SecretStr = Field(
        SecretStr("apikey"),
        frozen=True,  # prevents pydantic-settings changing the default value in the nested model
    )


class _MetOfficeClientConfigLive(BaseModel):
    client_type: Literal["live"]

    base_url: HttpUrl = Field(
        HttpUrl("https://data.hub.api.metoffice.gov.uk"),
        frozen=True,  # prevents pydantic-settings changing the default value in the nested model
    )
    secret: SecretStr = Field(
        ...,
        validation_alias="live_secret",
        description="The secret is required for live service as the user must register for the api.",
        min_length=10,
    )


class MetOfficeClientConfig(ClientModel):
    met_office: _MetOfficeClientConfigLive | _MetOfficeClientConfigMock = Field(
        default_factory=dict, discriminator="client_type"
    )

    def add_auth_header(self, request: httpx.Request) -> httpx.Request:
        """
        Attach the configured API key to the given HTTPX request's headers.

        Parameters:
            request (httpx.Request): The outgoing HTTP request to modify.

        Returns:
            httpx.Request: The same request instance with its "apikey" header set.
        """
        request.headers["apikey"] = self.met_office.secret.get_secret_value()
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
            base_url=self.met_office.base_url.encoded_string(),
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
            base_url=self.met_office.base_url.encoded_string(),
            auth=self.add_auth_header,
            headers={
                "accept": "application/json",
            },
        ) as session:
            yield session


async def get_observation_async(
    client_session: httpx.AsyncClient, geohash: str, version: str = "1"
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
    response = await client_session.get(f"/observation-land/{version}/{geohash}")
    response.raise_for_status()
    return response.content


def get_observation(
    client_session: httpx.Client, geohash: str, version: str = "1"
) -> bytes:
    """
    Fetches land observation data for the given geohash from the Met Office API.

    Parameters:
        geohash (str): Geohash identifying the observation location.

    Returns:
        bytes: Raw response body (JSON) returned by the API.
    """
    response = client_session.get(f"/observation-land/{version}/{geohash}")
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
    cfg = MetOfficeClientConfig()
    with cfg.api_client() as client:
        nearest = (
            One[MetOfficeLandObservationStation]
            .model_validate_json(get_nearest(client, 50.72, -3.53))
            .item
        )
        observation = (
            Some[MetOfficeLandObservationV1]
            .model_validate_json(get_observation(client, nearest.geohash))
            .root
        )
        print(observation, len(observation))
