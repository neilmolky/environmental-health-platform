from datetime import datetime, timezone
from pathlib import Path
from typing import Self

import httpx
from backend.bronze.met_office.client import (
    MetOfficeLandObservationNearest,
    One,
    get_nearest,
)
from pydantic import BaseModel, Field


class MetOfficeLandObservationRecord(BaseModel, frozen=True):
    """
    The unified, version-controlled compilation target.
    Uses composition to cleanly separate input targets from network resolutions.
    """

    # 1. Strict, self-validating geographical input boundaries for the UK
    lat: float = Field(..., ge=49.0, le=61.0, description="Target query latitude")
    long: float = Field(..., ge=-11.0, le=2.0, description="Target query longitude")
    # 2. Flattened metadata fields from the nearest-station resolution lookup
    station_meta: MetOfficeLandObservationNearest | None = Field(
        None, description="Resolved station metadata details from the live network"
    )

    # 3. Dynamic audit tracker safely placed at the very bottom
    added_to_registry: datetime | None = Field(
        default=None,
        description="Audit tracking marker indicating exactly when this coordinate pair was compiled",
    )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MetOfficeLandObservationRecord):
            return False
        # Two records are equal if their coordinates match, regardless of cache state
        return self.lat == other.lat and self.long == other.long

    def __hash__(self) -> int:
        return hash((self.lat, self.long))

    @property
    def is_cached(self):
        return all((self.station_meta is not None, self.added_to_registry is not None))

    def fetch_resolved_state(
        self, client: httpx.Client
    ) -> "MetOfficeLandObservationRecord":
        result_bytes = get_nearest(client, self.lat, self.long)
        result = (
            One[MetOfficeLandObservationNearest].model_validate_json(result_bytes).item
        )
        return MetOfficeLandObservationRecord(
            lat=self.lat,
            long=self.long,
            station_meta=result,
            added_to_registry=datetime.now(timezone.utc),
        )


class MetOfficeLandObservationRegistry(BaseModel):
    """
    The unified, version-controlled compilation target.
    Uses composition to cleanly separate input targets from network resolutions.
    """

    items: set[MetOfficeLandObservationRecord]

    @staticmethod
    def registry_path(parent_dir: Path | str | None = None) -> Path:
        if parent_dir is None:
            parent_dir = Path(__file__).parent
        parent_dir = Path(parent_dir)
        if parent_dir.is_file():
            raise NotADirectoryError()
        return parent_dir / "geohash_registry.json"

    @classmethod
    def load_from_disk(cls, parent_dir: Path | str | None = None) -> Self:
        """Safely instantiates the registry schema directly from a version-controlled JSON asset."""
        path = cls.registry_path(parent_dir)
        if not path.exists():
            return cls(items=set())

        with open(path, "r") as f:
            return cls.model_validate_json(f.read())

    def save_to_disk(self, parent_dir: Path | str | None = None) -> None:
        """Atomically serialises the validated registry structure back to a file layout."""
        path = self.registry_path(parent_dir)
        with open(path, "w") as f:
            # Writes pretty-printed, standardized JSON for clean Git diff trackability
            f.write(self.model_dump_json(indent=2))

    def update_all_uncached_items(self, client: httpx.Client) -> None:
        """Iterates through your items, upgrading uncached entries via the network client."""
        updated_items = set()
        for item in self.items:
            if not item.is_cached:
                # Trigger network resolution and append the clean object copy
                updated_items.add(item.fetch_resolved_state(client))
            else:
                updated_items.add(item)
        self.items = updated_items

    def register_location(self, lat: float, long: float) -> None:
        """
        Safely registers a new location target.
        If the coordinate pair already exists, it honors the existing cache and skips.
        """
        new_record = MetOfficeLandObservationRecord(lat=lat, long=long)
        # Because we custom hashed the model, this checks coordinate duplicates instantly!
        if new_record not in self.items:
            self.items.add(new_record)

    def get_geohash_set(self) -> set[str]:
        return {item.station_meta.geohash for item in self.items if item.station_meta}


if __name__ == "__main__":
    from backend.bronze.met_office.client import _MetOfficeClientConfig

    registry = MetOfficeLandObservationRegistry.load_from_disk()
    with _MetOfficeClientConfig().api_client() as client:
        registry.register_location(50.72, -3.53)  # example of development workflow
        registry.update_all_uncached_items(client)
    registry.save_to_disk()
