import math
import random
from datetime import datetime

import patito as pt
from polyfactory.factories.pydantic_factory import ModelFactory


class LatLon(pt.Model, frozen=True):
    """
    Helper Model, validates latitude and longitude values against permitted latitude and
    longitudes defined by Met Office Api

    frozen to enable hashing
    """

    lat: float = pt.Field(..., ge=-90.0, le=90.0, description="Target query latitude")
    lon: float = pt.Field(
        ..., ge=-180.0, le=180.0, description="Target query longitude"
    )

    def __str__(self) -> str:
        return f"{self.lat:+f},{self.lon:+f}"

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
            float: Latitude in degrees between 50.0 and 58.0 inclusive,
                   rounded to 4 decimal places.
        """
        return round(random.uniform(50.0, 58.0), 4)

    @classmethod
    def lon(cls) -> float:
        """
        Generate a longitude within the UK bounding box used by the factory.

        Returns:
            A longitude in decimal degrees between -7.0 and 1.5,
            rounded to 4 decimal places.
        """
        return round(random.uniform(-7.0, 1.5), 4)


class MetOfficeLandObservationV1(pt.Model):
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


class MetOfficeLandObservationV1Factory(ModelFactory[MetOfficeLandObservationV1]):
    __model__ = MetOfficeLandObservationV1


class MetOfficeLandObservationStationV1(pt.Model):
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
    ModelFactory[MetOfficeLandObservationStationV1]
):
    __model__ = MetOfficeLandObservationStationV1
