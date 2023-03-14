"""Shared fixtures and other pytest configuration"""

import os
import zipfile

import pytest
import xarray as xr
from dateutil.parser import parse as date_parse
from fastapi.testclient import TestClient
from httpx import Headers

from app.main import app
from app.services.data_zarr.data_service import DataService, get_data_service

# pylint: disable=line-too-long


@pytest.fixture(name="predictions_dataset")
def predictions_dataset_fixture() -> xr.Dataset:
    """Open a sample xarray Dataset that matches the production schema"""

    # Dimensions:    (time: 2, latitude: 10, longitude: 14)
    # Coordinates:
    #   * latitude   (latitude) float64 1.25 1.0 0.75 0.5 0.25 0 -0.25 -0.5 -0.75 -1.0
    #   * longitude  (longitude) float64 0.0 0.25 0.5 0.75 1.0 179.5 179.75 180.0 180.25 258.75 359.0 359.25 359.5 359.75
    #   * time       (time) datetime64[ns] 2021-01-01 2021-01-01T01:00:00

    if not os.path.exists("/tmp/dummy_small.zarr"):
        with zipfile.ZipFile("tests/dummy_small.zarr.zip", "r") as zip_ref:
            zip_ref.extractall("/tmp/dummy_small.zarr")

    return xr.open_zarr("/tmp/dummy_small.zarr")


@pytest.fixture(name="predictions_data_service")
def predictions_data_service_fixture(predictions_dataset: xr.Dataset) -> DataService:
    """Create DataService instance that wraps given xarray Dataset"""
    return DataService(predictions_dataset)


@pytest.fixture(name="test_client")
def test_client_fixture(predictions_data_service: DataService) -> TestClient:
    """Create TestClient instance that allow requests to our fastapi app"""
    client = TestClient(app)
    app.dependency_overrides[get_data_service] = lambda: predictions_data_service

    app.state.FROM_DATE = date_parse("2021-01-01T00:00:00")
    app.state.TO_DATE = date_parse("2021-01-01T03:00:00")
    app.state.predictions_filename = "/tmp/dummy_small.zarr"
    client.headers = Headers({"x-api-key": "any_key"})
    return client
