"""Property positions: an optional input that lets the analysis ask "is it my
neighbourhood?" as well as "is it me or the market?" (docs/methodology.md
section 13).

Positions are configuration, not review data: one row per property with
``property_id, lat, lon`` and an optional ``zone`` name. They come from a file the
team provides (never scraped) and are kept separate from the review files, because
``load_dir`` reads every CSV in a review folder as reviews.

Privacy (CLAUDE.md rule 4): an exact position identifies a real hotel even under
an anonymised name. ``coarsen`` snaps positions to a grid for anything public;
only SYNTHETIC positions are published as they are.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .loader import read_frame
from .schema import SchemaError

LOCATION_COLUMNS = ["property_id", "lat", "lon", "zone"]
EARTH_RADIUS_KM = 6371.0088  # mean Earth radius (IUGG)
PUBLIC_GRID_KM = 0.5  # grid that real positions are snapped to before publishing

_ALIASES: dict[str, tuple[str, ...]] = {
    "property_id": ("property_id", "property", "hotel_id", "hotel", "listing_id"),
    "lat": ("lat", "latitude", "y"),
    "lon": ("lon", "lng", "long", "longitude", "x"),
    "zone": ("zone", "area", "neighbourhood", "neighborhood", "locality"),
}


def _normalise_name(name: object) -> str:
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def validate_locations(frame: pd.DataFrame, properties=None) -> pd.DataFrame:
    """Map column aliases, check the values, and return ``LOCATION_COLUMNS``.

    ``properties`` (optional) are the property ids in the review data: a position
    for an unknown id is an error (usually a typo), while properties without a
    position are allowed and simply take no part in the neighbourhood analysis.
    """
    names = {_normalise_name(c): c for c in frame.columns}
    renamed = {}
    for canonical, aliases in _ALIASES.items():
        found = next((names[a] for a in aliases if a in names), None)
        if found is not None:
            renamed[found] = canonical
    out = frame.rename(columns=renamed)
    missing = [c for c in ("property_id", "lat", "lon") if c not in out.columns]
    if missing:
        raise SchemaError(f"Locations need columns {missing} (or an alias such as 'latitude').")
    if "zone" not in out.columns:
        out = out.assign(zone=None)
    out = out[LOCATION_COLUMNS].copy()
    out["property_id"] = out["property_id"].astype(str).str.strip()
    out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
    out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
    out["zone"] = out["zone"].astype(object).where(out["zone"].notna(), None)

    bad = out[out["lat"].isna() | out["lon"].isna()
              | ~out["lat"].between(-90, 90) | ~out["lon"].between(-180, 180)]
    if not bad.empty:
        raise SchemaError(
            f"Invalid coordinates for {sorted(bad['property_id'])}: lat must be in "
            "[-90, 90] and lon in [-180, 180]."
        )
    dupes = out["property_id"][out["property_id"].duplicated()]
    if not dupes.empty:
        raise SchemaError(f"More than one position for {sorted(set(dupes))}.")
    if properties is not None:
        unknown = sorted(set(out["property_id"]) - {str(p) for p in properties})
        if unknown:
            raise SchemaError(f"Positions for properties not in the reviews: {unknown}.")
    return out.reset_index(drop=True)


def load_locations(path: str | Path, properties=None) -> pd.DataFrame:
    """Load a CSV/JSON file of property positions (see ``validate_locations``)."""
    return validate_locations(read_frame(path), properties=properties)


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km; broadcasts over numpy arrays."""
    lat1, lon1, lat2, lon2 = (
        np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2)
    )
    h = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def distance_matrix(locations: pd.DataFrame) -> np.ndarray:
    """Pairwise distances in km, in the row order of ``locations``."""
    lat = locations["lat"].to_numpy(dtype=float)
    lon = locations["lon"].to_numpy(dtype=float)
    return haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])


def coarsen(locations: pd.DataFrame, grid_km: float = PUBLIC_GRID_KM) -> pd.DataFrame:
    """Snap positions to a ``grid_km`` grid (cell centres), for publishing real data.

    Nearby properties may then share a point; that is the intent.
    """
    if not grid_km > 0:
        raise ValueError(f"grid_km must be positive, got {grid_km!r}")
    lat0 = float(locations["lat"].mean()) if len(locations) else 0.0
    dlat = grid_km / 111.2
    dlon = grid_km / (111.2 * max(np.cos(np.radians(lat0)), 1e-6))
    lat = (np.floor(locations["lat"] / dlat) + 0.5) * dlat
    lon = (np.floor(locations["lon"] / dlon) + 0.5) * dlon
    return locations.assign(lat=lat.round(5), lon=lon.round(5))
