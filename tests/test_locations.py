import pandas as pd
import pytest

from cri.locations import (
    LOCATION_COLUMNS,
    coarsen,
    distance_matrix,
    haversine_km,
    load_locations,
    validate_locations,
)
from cri.schema import SchemaError


def _frame(**cols):
    base = {"property_id": ["A", "B"], "lat": [30.45, 30.46], "lon": [78.07, 78.08]}
    return pd.DataFrame({**base, **cols})


def test_aliases_are_mapped_and_zone_is_optional(tmp_path):
    path = tmp_path / "positions.csv"
    pd.DataFrame(
        {"Hotel": ["A", "B"], "Latitude": [30.45, 30.46], "lng": [78.07, 78.08]}
    ).to_csv(path, index=False)
    loc = load_locations(path)
    assert list(loc.columns) == LOCATION_COLUMNS
    assert loc["zone"].isna().all()
    assert list(loc["property_id"]) == ["A", "B"]


@pytest.mark.parametrize(
    "bad", [{"lat": [91.0, 30.0]}, {"lon": [78.0, -181.0]}, {"lat": ["x", 30.0]}]
)
def test_invalid_coordinates_are_rejected(bad):
    with pytest.raises(SchemaError, match="Invalid coordinates"):
        validate_locations(_frame(**bad))


def test_duplicate_and_unknown_properties_are_rejected():
    with pytest.raises(SchemaError, match="More than one position"):
        validate_locations(_frame(property_id=["A", "A"]))
    with pytest.raises(SchemaError, match="not in the reviews"):
        validate_locations(_frame(), properties=["A"])
    # Properties without a position are fine: they just take no part.
    assert len(validate_locations(_frame(), properties=["A", "B", "C"])) == 2


def test_missing_columns_are_named():
    with pytest.raises(SchemaError, match="lon"):
        validate_locations(pd.DataFrame({"property_id": ["A"], "lat": [30.0]}))


def test_haversine_known_distances():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.01)  # 1 degree of latitude
    assert haversine_km(30.45, 78.07, 30.45, 78.07) == 0
    d = distance_matrix(validate_locations(_frame()))
    assert d.shape == (2, 2) and d[0, 1] == pytest.approx(d[1, 0]) and d[0, 0] == 0


def test_coarsen_snaps_to_grid_cells():
    loc = validate_locations(
        pd.DataFrame({"property_id": ["A", "B", "C"], "lat": [30.4501, 30.4502, 30.47],
                      "lon": [78.0701, 78.0702, 78.09]})
    )
    out = coarsen(loc, grid_km=0.5)
    assert (out.loc[0, ["lat", "lon"]] == out.loc[1, ["lat", "lon"]]).all()  # same cell
    assert (out.loc[0, ["lat", "lon"]] != out.loc[2, ["lat", "lon"]]).any()
    # No snapped point is more than half a cell diagonal from the original.
    moved = haversine_km(loc["lat"], loc["lon"], out["lat"], out["lon"])
    assert (moved <= 0.5 * 2**0.5 / 2 + 0.01).all()
    with pytest.raises(ValueError):
        coarsen(loc, grid_km=0)
