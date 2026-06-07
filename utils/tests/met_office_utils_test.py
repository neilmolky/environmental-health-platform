from datetime import UTC, datetime

import pytest
from utils.met_office_models import (
    LatLon,
    MetOfficeLandObservationNearestFactory,
    MetOfficeLandObservationRecord,
)


@pytest.fixture
def greenwich() -> dict[str, float]:
    return {"lat": 51.4769, "lon": 0.0000}


def test_deduplication_logic(greenwich: dict[str, float]) -> None:
    unmodelled = LatLon.model_validate(greenwich)
    unresolved = MetOfficeLandObservationRecord.model_validate(greenwich)
    resolved = MetOfficeLandObservationRecord(
        **greenwich,
        station_meta=MetOfficeLandObservationNearestFactory.batch(size=1)[0],
        added_to_registry=datetime.now(UTC),
    )
    assert not unresolved.is_cached
    assert resolved.is_cached
    assert unresolved == resolved
    assert unmodelled != unresolved
    assert len({resolved, unresolved}) == 1


def test_haversine_distance(greenwich: dict[str, float]) -> None:
    greenwich_model = MetOfficeLandObservationRecord.model_validate(greenwich)
    sydney = MetOfficeLandObservationRecord(lat=-33.8688, lon=151.2093)
    expected_distance = pytest.approx(16987.86)
    calculated_distance = greenwich_model.haversine_distance(sydney)
    assert calculated_distance == expected_distance
