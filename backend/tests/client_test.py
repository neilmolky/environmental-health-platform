from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
from backend.bronze.met_office.client import (
    MET_OFFICE_LIVE_URL,
    MetOfficeLandObservationGeohash,
    MetOfficeLandObservationNearest,
    _MetOfficeClientConfig,
    get_nearest,
    get_observation,
    met_office_client_factory,
)
from pydantic import ValidationError
from utils.pydantic_utils import One, Some


class TestMetOfficeClient:
    """
    Live Integration Smoke Test. Verifies that live code models
    match live industry data structures exactly.
    """

    @pytest.fixture
    def config(self) -> _MetOfficeClientConfig:
        try:
            # Force use of live services
            return met_office_client_factory(use_mock=False)
        except ValidationError:
            pytest.fail(
                "Missing live infrastructure credentials! "
                "To run this test, set MET_OFFICE_CLIENT_ID, MET_OFFICE_CLIENT_SECRET, MET_OFFICE_BASE_URL. "
                f"Register for cretentials here {MET_OFFICE_LIVE_URL}. "
            )

    @pytest.fixture
    def client(self, config: _MetOfficeClientConfig) -> Generator[httpx.Client]:
        with config.api_client() as c:
            yield c

    @pytest.fixture
    async def async_client(
        self, config: _MetOfficeClientConfig
    ) -> AsyncGenerator[httpx.AsyncClient]:
        async with config.async_api_client() as c:
            yield c

    @pytest.mark.integration
    def test_endpoints_for_schema_drift(self, client: httpx.Client):
        # test simply runs with the pydantic validation to identify schema drift
        # might raise a connection error or validation error causing the test to fail
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
        for item in observation:
            assert item.datetime
