"""Unit tests for api module"""

import pytest
import xarray as xr
from dateutil.parser import parse as date_parse
from fastapi.testclient import TestClient
from httpx import QueryParams


def test_get_parameters(test_client: TestClient):
    """Check that parameter info is returned correctly"""

    response = test_client.get("/v1/forecast/parameters")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["TP"]
    assert res_json["TP"]["units"]
    assert res_json["TP"]["short_name"]
    assert res_json["TP"]["long_name"]


def test_get_single_point(test_client: TestClient, predictions_dataset: xr.Dataset):
    """Check coordinates and values of a single point"""

    params = QueryParams(
        {"lon": 1.0, "lat": 1.25, "parameters": "VAR_2T", "units": "SI", "freq": "5min"}
    )
    res = test_client.get("/v1/forecast", params=params).json()
    assert len(res["features"]) == 13  # Every 5 minutes, including start and end
    assert res["features"][0]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][-1]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][0]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"
    assert res["features"][-1]["properties"]["DATETIME"] == "2021-01-01T01:00:00Z"
    assert res["features"][12]["properties"]["VAR_2T"] == pytest.approx(
        predictions_dataset["VAR_2T"]
        .sel(
            time=date_parse("2021-01-01T01:00:00"),
            method="nearest",
            lon=1.0,
            lat=1.25,
        )
        .item(),
        0.00001,
    )


def test_get_multiple(
    test_client: TestClient,
):
    """Check coordinates and values of multiple points"""

    params = {"parameters": "VAR_2T", "units": "SI", "freq": "5min"}
    body = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1.0, 1.25]},
            },
            {
                "type": "Feature",
                "id": 1,
                "geometry": {"type": "Point", "coordinates": [0.5, 1.0]},
            },
        ],
    }
    res = test_client.post("/v1/forecast", params=params, json=body).json()

    assert len(res["features"]) == 2 * (
        12 + 1
    )  # Every 5 minutes, including start and end
    assert res["features"][0]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][12 + 1]["geometry"]["coordinates"] == [0.5, 1.0]
    assert res["features"][12 + 1]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"
    assert res["features"][12]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][12]["properties"]["DATETIME"] == "2021-01-01T01:00:00Z"


def test_pass_invalid_parameter_single(test_client: TestClient):
    """Check coordinates and values of a single point"""

    params = QueryParams(
        {"lon": 1.0, "lat": 1.25, "parameters": "VAR_2T,PACMAN", "units": "SI"}
    )
    response = test_client.get("/v1/forecast", params=params)
    assert response.status_code == 400
    resp_json = response.json()
    assert resp_json["detail"]
    assert resp_json["detail"] == "Parameters not supported: PACMAN"


def test_pass_invalid_parameter_multiple(test_client: TestClient):
    """Check coordinates and values of a single point"""

    params = {"parameters": "PACMAN,VAR_2T,MARIO", "units": "SI"}
    body = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1.0, 1.25]},
            },
            {
                "type": "Feature",
                "id": 1,
                "geometry": {"type": "Point", "coordinates": [0.5, 1.0]},
            },
        ],
    }

    response = test_client.post("/v1/forecast", params=params, json=body)
    assert response.status_code == 400
    res_json = response.json()
    assert res_json["detail"]
    assert res_json["detail"] == "Parameters not supported: MARIO, PACMAN"


def test_default_freq_param(test_client: TestClient, predictions_dataset: xr.Dataset):
    """Check coordinates and values of a single point"""

    params = QueryParams(
        {"lon": 1.0, "lat": 1.25, "parameters": "VAR_2T", "units": "SI"}
    )
    res = test_client.get("/v1/forecast", params=params).json()
    assert len(res["features"]) == 2
    assert res["features"][0]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][1]["geometry"]["coordinates"] == [1.0, 1.25]
    assert res["features"][0]["properties"]["DATETIME"] == "2021-01-01T00:00:00Z"
    assert res["features"][1]["properties"]["DATETIME"] == "2021-01-01T01:00:00Z"
    assert res["features"][1]["properties"]["VAR_2T"] == pytest.approx(
        predictions_dataset["VAR_2T"]
        .sel(
            time=date_parse("2021-01-01T01:00:00"),
            method="nearest",
            lon=1.0,
            lat=1.25,
        )
        .item(),
        0.00001,
    )
