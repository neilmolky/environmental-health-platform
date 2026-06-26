from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Literal

import httpx
from httpx import Response
from pydantic import BaseModel, Field, HttpUrl, SecretStr

from utils.api.base_client import ClientModel
from utils.models.generic import One, Some
from utils.models.met_office import (
    LatLon,
    MetOfficeLandObservationStationV1,
    MetOfficeLandObservationV1,
)

MET_OFFICE_LIVE_URL = "https://data.hub.api.metoffice.gov.uk"
MET_OFFICE_USER_URL = "https://datahub.metoffice.gov.uk"


class _MetOfficeClientConfigMock(BaseModel):
    client_type: Literal["mock"]

    base_url: HttpUrl = Field(
        ...,
        validation_alias="mock_url",
        description="The user must spin up a mock service and provide this url.",
    )
    secret: SecretStr = Field(
        SecretStr("apikey"),
        frozen=True,  # prevents pydantic-settings changing the default value
    )


class _MetOfficeClientConfigLive(BaseModel):
    client_type: Literal["live"]

    base_url: HttpUrl = Field(
        HttpUrl("https://data.hub.api.metoffice.gov.uk"),
        frozen=True,  # prevents pydantic-settings changing the default value
    )
    secret: SecretStr = Field(
        ...,
        validation_alias="live_secret",
        description="the user must register for the live api and provide this secret.",
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


async def aget_observation(
    client_session: httpx.AsyncClient, geohash: str, version: Literal["1"] = "1"
) -> Response:
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
    return response


def get_observation(
    client_session: httpx.Client, geohash: str, version: Literal["1"] = "1"
) -> Response:
    """
    Fetches land observation data for the given geohash from the Met Office API.

    Parameters:
        geohash (str): Geohash identifying the observation location.

    Returns:
        bytes: Raw response body (JSON) returned by the API.
    """
    response = client_session.get(f"/observation-land/{version}/{geohash}")
    response.raise_for_status()
    return response


async def aget_nearest(
    client: httpx.AsyncClient, lat: float, lon: float, version: Literal["1"] = "1"
) -> Response:
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
    response = await client.get(
        f"/observation-land/{version}/nearest", params=params.model_dump()
    )
    response.raise_for_status()
    return response


def get_nearest(
    client: httpx.Client, lat: float, lon: float, version: Literal["1"] = "1"
) -> Response:
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
    response = client.get(
        f"/observation-land/{version}/nearest", params=params.model_dump()
    )
    response.raise_for_status()
    return response


if __name__ == "__main__":
    cfg = MetOfficeClientConfig()
    with cfg.api_client() as client:
        nearest = (
            One[MetOfficeLandObservationStationV1]
            .model_validate_json(get_nearest(client, 50.72, -3.53).read())
            .item
        )
        observation = (
            Some[MetOfficeLandObservationV1]
            .model_validate_json(get_observation(client, nearest.geohash).read())
            .root
        )
        print(observation, len(observation))
