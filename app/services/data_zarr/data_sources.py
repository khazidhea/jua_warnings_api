"""Module containing classes/methods relevant"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar, Literal

import boto3


def get_timestep(current_time: datetime) -> str:
    """Depending on current timestamp,
    returns 00, 06, 12, 18"""
    if current_time.hour >= 18:
        return "18"
    if current_time.hour >= 12:
        return "12"
    if current_time.hour >= 6:
        return "06"
    return "00"


def get_zarr_filename(current_time: datetime) -> str:
    """Return the path to an individual zarr file based on the time"""
    datestr = current_time.strftime("%Y%m%d")
    timestep = get_timestep(current_time)
    return f"forecast_{datestr}{timestep}_000.zarr/"


def validate_s3_path(path: str) -> None:
    """Check that a given string is a valid S3 URL"""
    if not path.startswith("s3://"):
        raise ValueError(f"'{path}' is not a valid S3 URL")


class ForecastSource(ABC):
    """
    Abstraction of "something" that points to the latest available forecast file
    """

    type: ClassVar[Literal["s3", "dynamodb"]]
    resolution: Any

    @abstractmethod
    def find_latest_zarr(self) -> str | None:
        """
        Returns an S3 URI to the latest available zarr file. Returns None if not found.
        """

    def get_latest_zarr_path(self) -> str:
        """
        Finds an S3 URI to the latest available zarr file.
        Checks to see that the S3 URL is valid.
        Raises an error if not found or if the URL is invalid.
        """
        path = self.find_latest_zarr()
        if not path:
            raise FileNotFoundError(f"No zarr file found in {self.type}")
        validate_s3_path(path)
        return path


class DynamoDBForecastSource(ForecastSource):
    """
    DynamoDB-specific ForecastSource.
    Reads from a table to see if a new dataset is present.
    """

    type: ClassVar[Literal["dynamodb"]] = "dynamodb"
    forecast_table: str
    resolution: Literal["25x25", "1x1"]

    db_client: Any

    def __init__(
        self,
        forecast_table: str,
        resolution: Literal["25x25", "1x1"],
        db_client: Any = None,
    ) -> None:
        """Class init"""
        super().__init__()
        self.forecast_table = forecast_table
        self.resolution = resolution
        self.db_client = boto3.client("dynamodb") if db_client is None else db_client

    def find_latest_zarr(self) -> str | None:
        """
        Reads from a DynamoDB table and returns the value of
        ZarrS3Path for a given resolution, if it exists.
        """
        res = self.db_client.get_item(
            Key={"Resolution": {"S": self.resolution}},
            TableName=self.forecast_table,
            AttributesToGet=["ZarrS3Path"],
        )
        if "Item" not in res:
            return None

        zarr_s3_path: str = res["Item"]["ZarrS3Path"]["S"]
        logging.debug("Prediction file exists in DynamoDB: %s", zarr_s3_path)
        return zarr_s3_path
