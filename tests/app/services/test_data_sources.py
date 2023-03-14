"""Test the various data sources used in the application"""
from unittest.mock import MagicMock

import pytest

from app.services.data_zarr.data_sources import DynamoDBForecastSource


def test_dynamodb_forecast_source():
    """Happy path where the dataset attribute is present in DynamoDB"""
    dataset_path = (
        "s3://bronze-data-platform-prod/V0.1/forecasts/forecast_2023020818_000.zarr"
    )
    mock_response = {
        "Item": {"ZarrS3Path": {"S": dataset_path}},
    }
    db_client = MagicMock()
    db_client.get_item.return_value = mock_response

    forecast_source = DynamoDBForecastSource(
        forecast_table="test", resolution="25x25", db_client=db_client
    )
    assert forecast_source.get_latest_zarr_path() == dataset_path


def test_dynamodb_missing_forecast_source():
    """Case where DynamoDB table is empty or the specified resolution isn't found"""
    mock_response = {}
    db_client = MagicMock()
    db_client.get_item.return_value = mock_response

    forecast_source = DynamoDBForecastSource(
        forecast_table="test", resolution="1x1", db_client=db_client
    )
    with pytest.raises(FileNotFoundError):
        forecast_source.get_latest_zarr_path()


def test_dynamodb_invalid_s3_url():
    """Case where DynamoDB doesn't contain a valid S3 URL"""
    dataset_path = (
        "bronze-data-platform-prod/V0.1/forecasts/forecast_2023020818_000.zarr"
    )
    mock_response = {
        "Item": {"ZarrS3Path": {"S": dataset_path}},
    }
    db_client = MagicMock()
    db_client.get_item.return_value = mock_response

    forecast_source = DynamoDBForecastSource(
        forecast_table="test", resolution="1x1", db_client=db_client
    )
    with pytest.raises(ValueError):
        forecast_source.get_latest_zarr_path()


def test_dynamodb_resource_not_found():
    """Case where the DynamoDB table is specified incorrectly (not found)"""
    db_client = MagicMock()
    db_client.get_item.side_effect = Exception()

    forecast_source = DynamoDBForecastSource(
        forecast_table="test", resolution="1x1", db_client=db_client
    )
    with pytest.raises(Exception):
        forecast_source.get_latest_zarr_path()
