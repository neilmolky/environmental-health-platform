from collections.abc import Generator

import httpx
import pytest
from pydantic import ValidationError
from utils.pydantic_utils import One, Some

from backend.bronze.met_office.client import (
    MET_OFFICE_USER_URL,
    MetOfficeClientConfig,
    MetOfficeLandObservationStation,
    MetOfficeLandObservationV1,
    get_nearest,
    get_observation,
)


class TestMetOfficeClient:
    """
    Live Integration Smoke Test. Verifies that live code models
    match live industry data structures exactly.
    """

    @pytest.fixture
    def config(self, monkeypatch) -> MetOfficeClientConfig:
        monkeypatch.setenv("MET_OFFICE__CLIENT_TYPE", "live")
        try:
            # Force use of live services
            return MetOfficeClientConfig()
        except ValidationError:
            pytest.fail(
                "Missing live infrastructure credentials! "
                "To run this test, set MET_OFFICE__LIVE_SECRET. "
                f"Register for credentials here {MET_OFFICE_USER_URL}. "
            )

    @pytest.fixture
    def client(self, config: MetOfficeClientConfig) -> Generator[httpx.Client]:
        with config.api_client() as c:
            yield c

    @pytest.mark.integration
    def test_endpoints_for_schema_drift(self, client: httpx.Client) -> None:
        # test simply runs with the pydantic validation to identify schema drift
        # might raise a connection error or validation error causing the test to fail
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
        assert len(observation) > 0
        for item in observation:
            assert item.datetime
