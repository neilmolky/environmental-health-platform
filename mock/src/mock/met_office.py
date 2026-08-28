from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, model_validator
from utils.models.met_office import (
    GeoHash,
    LatLon,
    LatLonFactory,
    MetOfficeLandObservationStationV1,
    MetOfficeLandObservationStationV1Factory,
    MetOfficeLandObservationV1,
    MetOfficeLandObservationV1Factory,
)

API_KEY_HEADER = APIKeyHeader(name="apikey", auto_error=True)
MOCK_API_KEY = "apikey"


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
    if api_key != MOCK_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Unauthorized: Mock API key mismatch. "
                "Use mock credentials: 'apikey'. "
                "Live Credentials should never be injected into mocks."
            ),
        )
    return api_key


met_office_app = FastAPI(
    title="Met Office Mock Services",
    description="Entrypoint Met Office mock services",
    version="0.1.0",
    dependencies=[Security(validate_met_office_auth)],
)

# --- 3. STATEFUL RUNTIME DATABASE ---
# random seeds should return deterministic results
now = datetime.now(UTC)
LatLonFactory.seed_random(1)
MetOfficeLandObservationStationV1Factory.seed_random(1)

# observation stations have deterministic lat lon only
# the geohash should be similarly deterministic off the back of this
# names will change, modeling the names as an scd becomes possible
MOCK_STATION_COORDINATES: list[LatLon] = [
    LatLonFactory.build(lat=51.5074, lon=-0.1278),
    LatLonFactory.build(lat=55.9533, lon=-3.1883),
    LatLonFactory.build(lat=51.4816, lon=-3.1791),
    LatLonFactory.build(lat=53.4808, lon=-2.2426),
    LatLonFactory.build(lat=54.5973, lon=-5.9301),
]
MOCK_GEOHASH_DB: dict[GeoHash, MetOfficeLandObservationStationV1] = {
    coord.calculate_geohash(): MetOfficeLandObservationStationV1Factory.build(
        geohash=coord.calculate_geohash().geohash
    )
    for coord in MOCK_STATION_COORDINATES
}
MOCK_OBSERVATION_DB: dict[str, list[MetOfficeLandObservationV1]] = {
    coord.calculate_geohash().geohash: MetOfficeLandObservationV1Factory.batch(size=24)
    for coord in MOCK_STATION_COORDINATES
}


class CoordinateRequest(BaseModel):
    max: int = Query(1, ge=1, le=5)
    lat: float | None = Query(None, description="Latitude coordinate")
    lon: float | None = Query(None, description="Longitude coordinate")
    geohash: str | None = Query(None, description="GeoHash string")

    @model_validator(mode="after")
    def validate_model_get_type(self):
        self.get_type()

    def get_type(self) -> LatLon | GeoHash:
        has_latlon = self.lat is not None and self.lon is not None
        has_geohash = self.geohash is not None
        if has_latlon and has_geohash:
            raise ValueError(
                "User error, coordinates and geohash provided. use one or the other"
            )
        elif has_latlon:
            return LatLon(lat=self.lat, lon=self.lon)
        elif has_geohash:
            return GeoHash(geohash=self.geohash)
        raise ValueError("User error, neigher coordinates or geohash provided.")


# --- 4. MOCK API ENDPOINTS ---
# literal endpoint comes first!
@met_office_app.get(
    "/observation-land/1/nearest",
    response_model=list[MetOfficeLandObservationStationV1],
    status_code=status.HTTP_200_OK,
)
async def get_nearest(
    params: Annotated[CoordinateRequest, Depends()],
) -> list[MetOfficeLandObservationStationV1]:
    ordered_records = sorted(
        MOCK_STATION_COORDINATES, key=params.get_type().haversine_distance
    )
    return [
        MOCK_GEOHASH_DB[record.calculate_geohash()]
        for record in ordered_records[0 : params.max]
    ]


@met_office_app.get(
    "/observation-land/1/{geohash}",
    response_model=list[MetOfficeLandObservationV1],
    status_code=status.HTTP_200_OK,
)
async def get_observation_async(
    params: Annotated[GeoHash, Depends()],
) -> list[MetOfficeLandObservationV1]:
    if params.geohash not in MOCK_OBSERVATION_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geohash '{params.geohash}' not found in mock database. {MOCK_OBSERVATION_DB}",
        )
    return MOCK_OBSERVATION_DB[params.geohash]


print(MOCK_GEOHASH_DB)
