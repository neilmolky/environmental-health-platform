import math
import random
from datetime import datetime

from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, Field


class LatLon(BaseModel, frozen=True):
    """
    Helper Model, validates latitude and longitude values against permitted latitude and
    longitudes defined by Met Office Api

    frozen to enable hashing
    """

    lat: float = Field(..., ge=-90.0, le=90.0, description="Target query latitude")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Target query longitude")

    @property
    def lat_radians(self) -> float:
        """
        Latitude converted to radians.
        
        Returns:
            float: Latitude value expressed in radians.
        """
        return math.radians(self.lat)

    @property
    def lon_radians(self) -> float:
        """
        Convert the longitude to radians.
        
        Returns:
            Longitude in radians.
        """
        return math.radians(self.lon)

    def haversine_distance(self, other: "LatLon") -> float:
        """
        Compute the great-circle distance to another LatLon using the Haversine formula.
        
        Returns:
            distance_km (float): Distance in kilometers rounded to 2 decimal places.
        """
        dlat = other.lat_radians - self.lat_radians
        dlon = other.lon_radians - self.lon_radians

        # Haversine core math
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(self.lat_radians)
            * math.cos(other.lat_radians)
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in kilometers
        earth_radius_km = 6371.0
        return round(c * earth_radius_km, 2)


class LatLonFactory(ModelFactory[LatLon]):
    __model__ = LatLon

    # Force coordinates to always fall within a bounding box around the UK
    @classmethod
    def lat(cls) -> float:
        """
        Generate a latitude constrained to a UK bounding box.
        
        Returns:
            float: Latitude in degrees between 50.0 and 58.0 inclusive, rounded to 4 decimal places.
        """
        return round(random.uniform(50.0, 58.0), 4)

    @classmethod
    def lon(cls) -> float:
        """
        Generate a longitude within the UK bounding box used by the factory.
        
        Returns:
            A longitude in decimal degrees between -7.0 and 1.5, rounded to 4 decimal places.
        """
        return round(random.uniform(-7.0, 1.5), 4)


class MetOfficeLandObservation(BaseModel):
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


class MetOfficeLandObservationFactory(ModelFactory[MetOfficeLandObservation]):
    __model__ = MetOfficeLandObservation


class MetOfficeLandObservationStation(BaseModel):
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


class MetOfficeLandObservationStationFactory(
    ModelFactory[MetOfficeLandObservationStation]
):
    __model__ = MetOfficeLandObservationStation


class MetOfficeLandObservationRecord(LatLon, frozen=True):
    """
    The unified, version-controlled compilation target.
    Uses composition to cleanly separate input targets from network resolutions.
    """

    station_meta: MetOfficeLandObservationStation | None = Field(
        None, description="Resolved station metadata details from the live network"
    )
    added_to_registry: datetime | None = Field(
        default=None,
        description=(
            "Audit tracking marker indicating exactly when this coordinate pair "
            "was compiled"
        ),
    )

    def __eq__(self, other: object) -> bool:
        """
        Determine whether another record represents the same geographic coordinates.
        
        Returns:
            `True` if `other` is a `MetOfficeLandObservationRecord` with the same `lat` and `lon`, `False` otherwise.
        """
        if not isinstance(other, MetOfficeLandObservationRecord):
            return False
        # Two records are equal if their coordinates match, regardless of cache state
        return self.lat == other.lat and self.lon == other.lon

    def __hash__(self) -> int:
        """
        Compute a hash value for the record using its latitude and longitude.

        Returns:
            int: Hash derived from the `(lat, lon)` coordinate pair.
        """
        return hash((self.lat, self.lon))

    @property
    def is_cached(self) -> bool:
        """
        Indicates whether the record has both resolved station metadata and a registry timestamp.
        
        Returns:
            bool: `True` if both `station_meta` and `added_to_registry` are present, `False` otherwise.
        """
        return (self.station_meta is not None) and (self.added_to_registry is not None)
