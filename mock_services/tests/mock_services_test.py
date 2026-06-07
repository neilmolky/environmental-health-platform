from datetime import datetime

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from mock_services.main import (
    MOCK_GEOHASH_DB,
    MOCK_OBSERVATION_DB,
    MOCK_STATION_COORDINATES,
    VALID_API_KEY,
    app,
)


# Use standard standard sync TestClient for FastAPI endpoints
@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestMetOfficeMockApi:
    def test_missing_api_key_header(self, client: TestClient) -> None:
        """
        Endpoints should return 403 Forbidden if the header is missing.
        """
        response: httpx.Response = client.get(
            "/observation-land/1/nearest?latitude=51.5074&longitude=-0.1278"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"

    def test_invalid_api_key_header(self, client: TestClient) -> None:
        """
        Endpoints should return 401 Unauthorized if the header is incorrect.
        """
        headers = {"apikey": "wrong_key_123"}
        response: httpx.Response = client.get(
            "/observation-land/1/nearest?latitude=51.5074&longitude=-0.1278",
            headers=headers,
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Unauthorized" in response.json()["detail"]

    def test_get_nearest_station_success(self, client: TestClient) -> None:
        """
        Nearest endpoint correctly resolves the closest coordinates via Haversine.
        """
        headers = {"apikey": VALID_API_KEY}

        # Pull a real coordinate out of your stateful mock list to target it
        target_coord = MOCK_STATION_COORDINATES[0]
        params = {
            "lat": target_coord.lat,
            "lon": target_coord.lon,
        }

        response: httpx.Response = client.get(
            "/observation-land/1/nearest", params=params, headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        # Verify it actually fetched the expected data slice linked to this coordinate
        expected_geohash = MOCK_GEOHASH_DB[target_coord][0].geohash
        assert data[0]["geohash"] == expected_geohash

    def test_get_observation_history_success(self, client: TestClient) -> None:
        """
        Observation endpoint returns a full 48-hour history sequence.
        """
        headers = {"apikey": VALID_API_KEY}

        # Target an existing geohash in your initialized DB
        valid_geohash = list(MOCK_OBSERVATION_DB.keys())[0]

        response: httpx.Response = client.get(
            f"/observation-land/1/{valid_geohash}", headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 48  # Asserts the 48-hour range constraint you wrote

        # Ensure your custom timestamp injection loop worked as intended
        for item in data:
            assert "datetime" in item
            # Verify the string can parse back into a valid ISO timestamp format
            assert datetime.fromisoformat(item["datetime"].replace("Z", "+00:00"))

    def test_get_observation_history_404(self, client: TestClient) -> None:
        """
        Observation endpoint throws a 404 error if an invalid geohash is requested.
        """
        headers = {"apikey": VALID_API_KEY}
        invalid_geohash = "NON_EXISTENT_GEOHASH"

        response: httpx.Response = client.get(
            f"/observation-land/1/{invalid_geohash}", headers=headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert (
            response.json()["detail"]
            == f"Geohash '{invalid_geohash}' not found in mock database."
        )
