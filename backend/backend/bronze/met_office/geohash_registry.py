import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import httpx
from backend.bronze.met_office.client import (
    MetOfficeLandObservationNearest,
    One,
    get_nearest,
)
from pydantic import BaseModel
from utils.met_office_models import MetOfficeLandObservationRecord


def fetch_resolved_state(
    record: MetOfficeLandObservationRecord, client: httpx.Client
) -> "MetOfficeLandObservationRecord":
    """
    Fetch resolved station metadata for this coordinate and return a new record
    populated with that metadata and a current UTC registry timestamp.

    Returns:
        MetOfficeLandObservationRecord: A new record with the same `lat` and `lon`,
        `station_meta` set to the resolved nearest-station metadata,
        and `added_to_registry` set to the current UTC datetime.
    """
    result_bytes = get_nearest(client, record.lat, record.lon)
    result = One[MetOfficeLandObservationNearest].model_validate_json(result_bytes).item
    return MetOfficeLandObservationRecord(
        lat=record.lat,
        lon=record.lon,
        station_meta=result,
        added_to_registry=datetime.now(UTC),
    )


class MetOfficeLandObservationRegistry(BaseModel):
    """
    The unified, version-controlled compilation target.
    Uses composition to cleanly separate input targets from network resolutions.
    """

    items: set[MetOfficeLandObservationRecord]

    @staticmethod
    def registry_path(parent_dir: Path | str | None = None) -> Path:
        """
        the path to the geohash registry file inside the parent directory.

        Parameters:
            parent_dir (Path | str | None): Directory containing the registry file;
            if None, uses the directory of this module.

        Returns:
            Path: Path to "geohash_registry.json" inside `parent_dir`.

        Raises:
            NotADirectoryError: If `parent_dir` is a file rather than a directory.
        """
        if parent_dir is None:
            parent_dir = Path(__file__).parent
        parent_dir = Path(parent_dir)
        if parent_dir.is_file():
            raise NotADirectoryError()
        return parent_dir / "geohash_registry.json"

    @classmethod
    def load_from_disk(cls, parent_dir: Path | str | None = None) -> Self:
        """
        Instantiate a MetOfficeLandObservationRegistry from the registry JSON on disk,
        or return an empty registry if the file is absent.

        Parameters:
            parent_dir (Path | str | None): Directory containing the registry file;
            if None the module's parent directory is used.

        Returns:
            MetOfficeLandObservationRegistry: The registry loaded from disk,
            or an empty registry when the registry file does not exist.
        """
        path = cls.registry_path(parent_dir)
        if not path.exists():
            return cls(items=set())

        with open(path) as f:
            return cls.model_validate_json(f.read())

    def save_to_disk(self, parent_dir: Path | str | None = None) -> None:
        """
        Persist the registry to disk in an atomic, crash-safe manner.

        Writes the registry as pretty-printed JSON to a file in the parent_dir,
        fsyncs the temp file to ensure data is flushed to disk, and then atomically
        replaces the target registry file with the temp file.
        On error, the temporary file is removed before the exception is propagated.

        Parameters:
            parent_dir (Path | str | None): Directory to store the registry file in;
            if `None`, the module directory is used to locate `geohash_registry.json`.
        """
        path = self.registry_path(parent_dir)
        # Write to a temporary file in the same directory
        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w") as f:
                # Writes pretty-printed, standardized JSON for clean Git diff's
                f.write(self.model_dump_json(indent=2))
                f.flush()
                os.fsync(f.fileno())
            # Atomically replace the target file
            os.replace(temp_path, path)
        except Exception:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise

    def update_all_uncached_items(self, client: httpx.Client) -> None:
        """
        Resolve and cache registry records that are not yet populated with
        station metadata.

        For each item in the registry, replaces uncached records with a resolved copy
        obtained using the provided HTTP client; items that are already cached are kept
        unchanged. After this call, `self.items` is updated with the new set of records.

        Parameters:
            client (httpx.Client): HTTP client used to fetch nearest-station data for
            uncached records.
        """
        updated_items = set()
        for item in self.items:
            if not item.is_cached:
                # Trigger network resolution and append the clean object copy
                updated_items.add(fetch_resolved_state(item, client))
            else:
                updated_items.add(item)
        self.items = updated_items

    def register_location(self, lat: float, lon: float) -> None:
        """
        Register a coordinate pair in the registry;
        if the same latitude/longitude is already present, do nothing.

        Parameters:
            lat (float): Latitude in degrees; must be between 49.0 and 61.0.
            long (float): Longitude in degrees; must be between -11.0 and 2.0.

        """
        new_record = MetOfficeLandObservationRecord(lat=lat, lon=lon)
        if new_record not in self.items:
            self.items.add(new_record)

    def get_geohash_set(self) -> set[str]:
        """
        Return the set of geohash identifiers from registry items that have resolved
        station metadata.

        Returns:
            set[str]: Geohash strings from each item's `station_meta.geohash` for items
            where `station_meta` is present.
        """
        return {item.station_meta.geohash for item in self.items if item.station_meta}


if __name__ == "__main__":
    from backend.bronze.met_office.client import _MetOfficeClientConfig

    registry = MetOfficeLandObservationRegistry.load_from_disk()
    with _MetOfficeClientConfig().api_client() as client:
        registry.register_location(50.72, -3.53)  # example of development workflow
        registry.update_all_uncached_items(client)
    registry.save_to_disk()
