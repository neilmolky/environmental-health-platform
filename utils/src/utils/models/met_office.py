import math
from datetime import datetime

import patito as pt
import pendulum
from faker import Faker
from pendulum import duration, interval
from polyfactory import Use
from polyfactory.factories.pydantic_factory import ModelFactory
from pygeohash import geohash

TRUE_BRITISH_FAKES = Faker("en_GB")


class GeoHash(pt.Model, frozen=True):
    """
    Helper Model, validates geohash values defined by Met Office Api

    frozen to enable hashing
    """

    geohash: str = pt.Field(
        pattern=r"[0-9b-hj-km-np-z]{5,6}",
        description="Valid Base32 geohash at regional (5) or station (6) precision.",
    )

    def __str__(self) -> str:
        return f"geohash{self.geohash}"

    def haversine_distance(self, other: "LatLon") -> float:
        decoded = geohash.decode(self.geohash)
        return LatLon(lat=decoded.latitude, lon=decoded.longitude).haversine_distance(
            other
        )


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
        return f"lat{self.lat:.6f}lon{self.lon:.6f}"

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

    def calculate_geohash(self) -> GeoHash:
        return GeoHash(geohash=geohash.encode(self.lat, self.lon, 6))


class LatLonFactory(ModelFactory[LatLon]):
    lat = Use(ModelFactory.__random__.uniform, 50.0, 58.0)
    lon = Use(ModelFactory.__random__.uniform, -7.0, 1.5)


class MetOfficeLandObservationV1(pt.Model, frozen=True):
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


COMPASS_POINTS = (
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
)


class MetOfficeLandObservationV1Factory(ModelFactory[MetOfficeLandObservationV1]):
    __model__ = MetOfficeLandObservationV1
    __faker__ = TRUE_BRITISH_FAKES
    humidity = Use(ModelFactory.__random__.randint, 0, 100)
    mslp = Use(ModelFactory.__random__.randint, 950, 1150)
    pressure_tendency = Use(ModelFactory.__random__.choice, ("R", "F", "S"))
    temperature = Use(ModelFactory.__random__.uniform, 0, 35)
    visibility = Use(ModelFactory.__random__.randint, 50, 5000)
    weather_code = Use(ModelFactory.__random__.randint, 10, 99)
    wind_direction = Use(ModelFactory.__random__.choice, COMPASS_POINTS)
    wind_gust = Use(ModelFactory.__random__.randint, 0, 10)
    wind_speed = Use(ModelFactory.__random__.uniform, 0, 90)

    @classmethod
    def batch(cls, size: int, **kwargs) -> list[MetOfficeLandObservationV1]:
        """the batch method will create incrementing datetimes in 3h intervals.

        Params:
            size: the number of intervals to generate
        """
        start = kwargs.pop("datetime", pendulum.now("UTC"))
        end = start - duration(hours=3 * size)
        return [
            cls.build(datetime=dt, **kwargs)
            for dt in interval(start, end).range("hours", 3)
        ]


class MetOfficeLandObservationStationV1(GeoHash, frozen=True):
    area: str
    """Location area"""
    region: str | None
    """Region code for UK locations"""
    country: str | None
    """The country of the location"""
    olson_time_zone: str | None
    """Olson time zone string of location"""


class MetOfficeLandObservationStationV1Factory(
    ModelFactory[MetOfficeLandObservationStationV1]
):
    area = Use(TRUE_BRITISH_FAKES.city)
    region = Use(TRUE_BRITISH_FAKES.county)
    country = Use(TRUE_BRITISH_FAKES.country)
    olson_time_zone = Use(TRUE_BRITISH_FAKES.timezone)


if __name__ == "__main__":
    print(MetOfficeLandObservationV1Factory.batch(5))
