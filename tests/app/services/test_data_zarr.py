"""Unit tests for data_zarr module"""

from math import atan2, degrees, sqrt

import pytest
import xarray as xr
from dateutil.parser import parse as date_parse

from app.services.data_zarr.data_service import DataService
from app.services.data_zarr.params import Frequency, UnitSystem


def test_get_single_point(
    predictions_data_service: DataService, predictions_dataset: xr.Dataset
):
    """Check coordinates and values of a single point"""
    res = predictions_data_service.get_points_as_geojson(
        [(1.0, 1.25)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T03:00:00")),
        ["VAR_2T", "TP"],
        units=UnitSystem.SI,
        freq=Frequency.FIVE_MINUTE,
    )
    assert len(res["features"]) == 13  # Every 5 minutes, including start and end
    assert res["features"][0]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][0]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"
    assert res["features"][-1]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][-1]["properties"]["DATETIME"] == "2021-01-01T01:00:00Z"
    assert res["features"][12]["properties"]["VAR_2T"] == pytest.approx(
        predictions_dataset["VAR_2T"]
        .sel(
            lon=1.0,
            lat=1.25,
            time=date_parse("2021-01-01T01:00:00"),
            method="nearest",
        )
        .item(),
        0.00001,
    )


def test_get_parameters(predictions_data_service: DataService):
    """Check that parameter info is returned correctly"""
    res = predictions_data_service.get_parameters(UnitSystem.DEFAULT)
    assert "TP" in res


def test_get_wind_values(predictions_data_service: DataService):
    """Check coordinates and values of a single point"""
    res = predictions_data_service.get_points_as_geojson(
        [(1.0, 1.25)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T03:00:00")),
        ["10WS", "10WD", "VAR_10U", "VAR_10V"],
        units=UnitSystem.SI,
        freq=Frequency.FIVE_MINUTE,
    )
    assert len(res["features"]) == 13  # Every 5 minutes, including start and end

    props = res["features"][0]["properties"]
    u_component = props["VAR_10U"]
    v_component = props["VAR_10V"]
    expected_wind_speed = sqrt(u_component**2 + v_component**2)
    expected_wind_direction = 90.0 - degrees(atan2(-v_component, -u_component))

    assert props["10WS"] == pytest.approx(expected_wind_speed, 0.000001)
    assert props["10WD"] == pytest.approx(expected_wind_direction, 0.000001)


def test_interpolated_temperature(predictions_data_service: DataService):
    """Check coordinates and temperature of a single interpolated point"""
    res = predictions_data_service.get_points_as_geojson(
        [(1.0, 1.25)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T03:00:00")),
        ["VAR_2T", "TP"],
        units=UnitSystem.SI,
        freq=Frequency.FIVE_MINUTE,
    )
    assert res["features"][0]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"
    assert res["features"][0]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][12]["properties"]["DATETIME"] == "2021-01-01T01:00:00Z"
    assert res["features"][12]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][6]["properties"]["DATETIME"] == "2021-01-01T00:30:00Z"
    assert res["features"][6]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][6]["properties"]["VAR_2T"] == pytest.approx(
        299.547119140625, 0.0000001
    )


def test_interpolated_precipitation(predictions_data_service: DataService):
    """Check coordinates and total precipitation of a single interpolated point"""
    res = predictions_data_service.get_points_as_geojson(
        [(1.1, 1.26)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T03:00:00")),
        ["VAR_2T", "TP"],
        units=UnitSystem.SI,
        freq=Frequency.FIVE_MINUTE,
    )

    assert res["features"][0]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"
    assert res["features"][0]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][12]["properties"]["DATETIME"] == "2021-01-01T01:00:00Z"
    assert res["features"][12]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][6]["properties"]["DATETIME"] == "2021-01-01T00:30:00Z"
    assert res["features"][6]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][6]["properties"]["TP"] == pytest.approx(
        1.4469337656919379e-05, 0.000001
    )


def test_get_multiple(predictions_data_service: DataService):
    """Check coordinates and values of multiple points"""
    res = predictions_data_service.get_points_as_geojson(
        [(1.0, 1.25), (0.5, 1.0)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T01:00:00")),
        ["VAR_2T"],
        units=UnitSystem.SI,
        freq=Frequency.FIVE_MINUTE,
    )
    assert len(res["features"]) == 2 * (
        12 + 1
    )  # Every 5 minutes, including start and end
    assert res["features"][0]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][12]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][12]["properties"]["DATETIME"] == "2021-01-01T01:00:00Z"
    assert res["features"][12 + 1]["geometry"]["coordinates"] == [0.5, 1.0]
    assert res["features"][12 + 1]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"


def test_get_point_antimeridian(
    predictions_data_service: DataService, predictions_dataset: xr.Dataset
):
    """Check coordinates and values of a point near the antimeridian"""
    res = predictions_data_service.get_points_as_geojson(
        [(-179.99, 0.01)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T03:00:00")),
        ["VAR_2T", "TP"],
        units=UnitSystem.SI,
        freq=Frequency.FIVE_MINUTE,
    )
    assert res["features"][0]["geometry"]["coordinates"] == [180.0, 0.0]
    assert res["features"][0]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"
    assert res["features"][0]["properties"]["VAR_2T"] == pytest.approx(
        predictions_dataset["VAR_2T"]
        .sel(
            lon=180.0,
            lat=0.0,
            time=date_parse("2021-01-01T00:00:00"),
            method="nearest",
        )
        .item(),
        0.00001,
    )


def test_get_point_meridian(
    predictions_data_service: DataService, predictions_dataset: xr.Dataset
):
    """Check coordinates and values of a point near the meridian"""
    res = predictions_data_service.get_points_as_geojson(
        [(-0.01, 0.01)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T03:00:00")),
        ["VAR_2T", "TP"],
        units=UnitSystem.SI,
        freq=Frequency.FIVE_MINUTE,
    )
    # Note this is returning data for (-0.25, 0) instead of the expected (0, 0)
    # due to xarray not crossing the meridian when finding nearest point
    assert res["features"][0]["geometry"]["coordinates"] == [-0.25, 0.0]
    assert res["features"][0]["properties"]["VAR_2T"] == pytest.approx(
        predictions_dataset["VAR_2T"]
        .sel(
            lon=360.0 - 0.25,
            lat=0.0,
            time=date_parse("2021-01-01T00:00:00"),
            method="nearest",
        )
        .item(),
        0.00001,
    )


def test_convert_to_default(
    predictions_data_service: DataService, predictions_dataset: xr.Dataset
):
    """Check coordinates and values of a point near the meridian"""
    res = predictions_data_service.get_points_as_geojson(
        [(-0.01, 0.01)],
        (date_parse("2021-01-01T00:00:00"), date_parse("2021-01-01T03:00:00")),
        ["VAR_2T", "TP"],
        units=UnitSystem.DEFAULT,
        freq=Frequency.FIVE_MINUTE,
    )
    assert res["features"][0]["properties"]["TP"] == pytest.approx(
        predictions_dataset["TP"]
        .sel(
            lon=360.0 - 0.25,
            lat=0.0,
            time=date_parse("2021-01-01T00:00:00"),
            method="nearest",
        )
        .item()
        / 12
        * 1000,
        0.0001,
    )
    assert res["features"][0]["properties"]["VAR_2T"] == pytest.approx(
        kelvin_to_degc(
            predictions_dataset["VAR_2T"]
            .sel(
                lon=360.0 - 0.25,
                lat=0.0,
                time=date_parse("2021-01-01T00:00:00"),
                method="nearest",
            )
            .item()
        ),
        0.0001,
    )


def kelvin_to_degc(temperature: float) -> float:
    """Helper to convert Kelvin temperature to degrees Celsius"""
    return temperature - 273.15
