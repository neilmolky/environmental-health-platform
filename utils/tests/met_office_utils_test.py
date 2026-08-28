import pytest
from utils.models.met_office import (
    LatLon,
)


@pytest.fixture
def greenwich() -> dict[str, float]:
    return {"lat": 51.4769, "lon": 0.0000}


def test_haversine_distance(greenwich: dict[str, float]) -> None:
    greenwich_model = LatLon.model_validate(greenwich)
    sydney = LatLon(lat=-33.8688, lon=151.2093)
    expected_distance = pytest.approx(16987.86)
    calculated_distance = greenwich_model.haversine_distance(sydney)
    assert calculated_distance == expected_distance
