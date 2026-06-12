from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader
from utils.met_office_models import (
    LatLon,
    LatLonFactory,
    MetOfficeLandObservation,
    MetOfficeLandObservationFactory,
    MetOfficeLandObservationStation,
    MetOfficeLandObservationStationFactory,
)

# Define the expected header name (adjust to match what your real API expects)
API_KEY_HEADER = APIKeyHeader(name="apikey", auto_error=True)

# Mocked valid token for testing
VALID_API_KEY = "apikey"


async def validate_met_office_auth(
    api_key: Annotated[str, Security(API_KEY_HEADER)],
) -> str:
    """
    Ensure the provided API key matches the service's expected mock API key.

    Parameters:
        api_key (str): API key extracted from the `apikey` request header.

    Returns:
        str: The validated API key string.

    Raises:
        HTTPException: With status code 401
            when the provided API key does not match the expected mock key.
    """
    if api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Unauthorized: Mock API key mismatch. "
                "Expected mock credentials: 'apikey'. "
                "Live Credentials should never be injected into mocks."
            ),
        )
    return api_key


app = FastAPI(
    title="Mock Service for Met Office via Polyfactory",
    description="A mock API with auto-generated data.",
    version="0.1.0",
    dependencies=[Security(validate_met_office_auth)],
)


# --- 3. STATEFUL RUNTIME DATABASE ---
MOCK_STATION_COORDINATES: list[LatLon] = LatLonFactory.batch(size=5)
MOCK_GEOHASH_DB: dict[LatLon, list[MetOfficeLandObservationStation]] = {
    coord: MetOfficeLandObservationStationFactory.batch(size=1)
    for coord in MOCK_STATION_COORDINATES
}
MOCK_OBSERVATION_DB: dict[str, list[MetOfficeLandObservation]] = {}

now = datetime.now(UTC)

for record in MOCK_GEOHASH_DB.values():
    geohash_key = record[0].geohash
    station_history: list[MetOfficeLandObservation] = []

    for hour_offset in range(48):
        # Calculate the exact timestamp for this hour slot (moving backwards)
        # Offset 0 is "now", offset 47 is "47 hours ago"
        target_timestamp = now - timedelta(hours=hour_offset)

        # Build a single randomized mock payload using Polyfactory,
        # but explicitly override the 'datetime' field with our calculated sequence!
        mock_observation = MetOfficeLandObservationFactory.build(
            datetime=target_timestamp
        )

        station_history.append(mock_observation)

    MOCK_OBSERVATION_DB[geohash_key] = station_history


# --- 4. MOCK API ENDPOINTS ---
# literal endpoint comes first!
@app.get(
    "/observation-land/1/nearest",
    response_model=list[MetOfficeLandObservationStation],
    status_code=status.HTTP_200_OK,
)
async def get_nearest(
    coordinates: Annotated[LatLon, Query()],
) -> list[MetOfficeLandObservationStation]:
    """
    Finds the mock station list nearest to the provided coordinates.

    Parameters:
        coordinates (LatLon): Query coordinates used to select the nearest mock station.

    Returns:
        list[MetOfficeLandObservationStation]:
            The list of observation station records associated with the
            nearest station's geohash.
    """
    key = min(MOCK_STATION_COORDINATES, key=coordinates.haversine_distance)
    return MOCK_GEOHASH_DB[key]


@app.get(
    "/observation-land/1/{geohash}",
    response_model=list[MetOfficeLandObservation],
    status_code=status.HTTP_200_OK,
)
async def get_observation_async(geohash: str) -> list[MetOfficeLandObservation]:
    """
    Retrieve the list of mock land observations for the specified geohash.

    Parameters:
        geohash (str): Geohash key identifying the mock observation history to return.

    Returns:
        list[MetOfficeLandObservation]:
            The list of stored observations for the given geohash.

    Raises:
        HTTPException: 404 Not Found if the geohash is not present in the mock database.
    """
    if geohash not in MOCK_OBSERVATION_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geohash '{geohash}' not found in mock database.",
        )
    return MOCK_OBSERVATION_DB[geohash]
