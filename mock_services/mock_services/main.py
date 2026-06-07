import random
from datetime import datetime, timedelta, timezone
from typing import Annotated, List

from fastapi import FastAPI, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader
from polyfactory.factories.pydantic_factory import ModelFactory
from utils.met_office_models import (
    LatLon,
    MetOfficeLandObservationGeohash,
    MetOfficeLandObservationNearest,
)

# Define the expected header name (adjust to match what your real API expects)
API_KEY_HEADER = APIKeyHeader(name="apikey", auto_error=True)

# Mocked valid token for testing
VALID_API_KEY = "apikey"


async def validate_met_office_auth(api_key: Annotated[str, Security(API_KEY_HEADER)]):
    """
    Validates that the incoming request header matches the mock credential
    provided by met_office_client_factory().
    """
    if api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Mock API key mismatch. Expected mock credentials: 'apikey'. Live Credentials should never be injected into mocks.",
        )
    return api_key


app = FastAPI(
    title="Mock Service for Met Office via Polyfactory",
    description="A mock API with auto-generated data.",
    version="0.1.0",
    dependencies=[Security(validate_met_office_auth)],
)


# --- 2. POLYFACTORY DATA FACTORY ---
class LatLonFactory(ModelFactory[LatLon]):
    __model__ = LatLon

    # Force coordinates to always fall within a bounding box around the UK
    @classmethod
    def lat(cls) -> float:
        return round(random.uniform(50.0, 58.0), 4)

    @classmethod
    def lon(cls) -> float:
        return round(random.uniform(-7.0, 1.5), 4)


class MetOfficeLandObservationGeohashFactory(
    ModelFactory[MetOfficeLandObservationGeohash]
):
    __model__ = MetOfficeLandObservationGeohash


class MetOfficeLandObservationNearestFactory(
    ModelFactory[MetOfficeLandObservationNearest]
):
    __model__ = MetOfficeLandObservationNearest


# --- 3. STATEFUL RUNTIME DATABASE ---
# Generate 5 completely valid, randomized observation stations instantly on startup
MOCK_STATION_COORDINATES: list[LatLon] = LatLonFactory.batch(size=5)
MOCK_GEOHASH_DB: dict[LatLon, list[MetOfficeLandObservationNearest]] = {
    coord: MetOfficeLandObservationNearestFactory.batch(size=1)
    for coord in MOCK_STATION_COORDINATES
}
# Generate 48 hours worth of randomized observations for each station instantly on startup
MOCK_OBSERVATION_DB: dict[str, list[MetOfficeLandObservationGeohash]] = {}

# Capture the exact current baseline time
now = datetime.now(timezone.utc)

for record in MOCK_GEOHASH_DB.values():
    geohash_key = record[0].geohash
    station_history = []

    # Loop exactly 48 times to build an hourly historical series
    for hour_offset in range(48):
        # Calculate the exact timestamp for this hour slot (moving backwards)
        # Offset 0 is "now", offset 47 is "47 hours ago"
        target_timestamp = now - timedelta(hours=hour_offset)

        # Build a single randomized mock payload using Polyfactory,
        # but explicitly override the 'datetime' field with our calculated sequence!
        mock_observation = MetOfficeLandObservationGeohashFactory.build(
            datetime=target_timestamp  # Supplying this cancels Polyfactory's random generator
        )

        station_history.append(mock_observation)


# --- 4. MOCK API ENDPOINTS ---
# literal endpoint comes first!
@app.get(
    "/observation-land/1/nearest",
    response_model=List[MetOfficeLandObservationNearest],
    status_code=status.HTTP_200_OK,
)
async def get_nearest(coordinates: Annotated[LatLon, Query()]):
    key = min(MOCK_STATION_COORDINATES, key=coordinates.haversine_distance)
    return MOCK_GEOHASH_DB[key]


@app.get(
    "/observation-land/1/{geohash}",
    response_model=List[MetOfficeLandObservationNearest],
    status_code=status.HTTP_200_OK,
)
async def get_observation_async(geohash: str):
    if geohash not in MOCK_OBSERVATION_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geohash '{geohash}' not found in mock database.",
        )
    return MOCK_OBSERVATION_DB[geohash]
