"""Module service working with zarr dataset."""

import logging
from datetime import datetime, time, timedelta
from typing import Any, Collection, Hashable, MutableMapping

import numpy as np
import pandas as pd
import xarray as xr
from fastapi import Request

from app.services.data_zarr.data_sources import DynamoDBForecastSource, ForecastSource
from app.services.data_zarr.params import Frequency, UnitSystem, gen_supported_params
from config import get_config

c = get_config()


class DataService:
    """Expose predictions dataset"""

    def __init__(self, dataset: xr.Dataset):
        self.dataset = dataset
        self.supported_params = gen_supported_params(dataset)

        # Pre-render parameter JSON dict
        self.params_json = {
            UnitSystem.SI: {
                k: v.to_json(UnitSystem.SI) for k, v in self.supported_params.items()
            },
            UnitSystem.DEFAULT: {
                k: v.to_json(UnitSystem.DEFAULT)
                for k, v in self.supported_params.items()
            },
        }

    def get_parameters(self, units: UnitSystem) -> dict:
        """get parameters list"""
        return self.params_json[units]

    def get_points_as_geojson(
        self,
        coords: list[tuple[float, float]],
        date_range: tuple[datetime, datetime],
        requested_params: Collection[str],
        requested_feature_ids: list[int | str | None] | None = None,
        units: UnitSystem = UnitSystem.DEFAULT,
        freq: Frequency = Frequency.ONE_HOUR,
    ) -> dict:
        """load the zarr data and render it as a GeoJSON feature collection"""

        requested_params = set(requested_params)
        self.check_params_supported(requested_params)

        lon, lat = [np.array(list(c)) for c in zip(*coords)]

        # We need to convert longitude from GeoJSON (-180,180] to zarr [0,360)
        lon = longitude_geojson_to_zarr(lon)

        param_specs = [self.supported_params[k] for k in requested_params]
        data_keys = {key for spec in param_specs for key in spec.data_keys}

        point_data = self._load_subset(lon, lat, date_range, data_keys)
        if freq != Frequency.ONE_HOUR:
            point_data = self._downscale_to_freq(point_data, freq=freq)
        point_data = self._calculate_output_values(requested_params, point_data)
        point_data = self._convert_units(requested_params, units, point_data)

        return _render_points_geojson(
            requested_params, point_data, requested_feature_ids
        )

    def get_unsupported_params(self, parameters: set[str]) -> set[str]:
        """Get parameters not supported by this data service"""
        return parameters - self.supported_params.keys()

    def check_params_supported(self, requested_params: set[str]) -> None:
        """Raise a ParamNotSupportedError if some params not supported"""
        unsupported_params = self.get_unsupported_params(requested_params)
        if unsupported_params:
            raise ParamNotSupportedError(unsupported_params)

    def _load_subset(
        self,
        lon: np.ndarray,
        lat: np.ndarray,
        date_range: tuple[datetime, datetime],
        data_keys: set[str],
    ) -> xr.Dataset:
        """
        Load the relevant xarray data from zarr storage for all provided coordinates
        """
        requested_start_date, requested_end_date = date_range
        point_data = (
            self.dataset[data_keys]
            .sel(
                lon=xr.DataArray(lon, dims="z"),
                lat=xr.DataArray(lat, dims="z"),
                method="nearest",
            )
            .compute()
        )
        range_start = np.max(
            [
                np.datetime64(requested_start_date),
                np.datetime64(point_data.time.min().item(), "ns"),
            ]
        )
        range_end = np.min(
            [
                np.datetime64(requested_end_date),
                np.datetime64(point_data.time.max().item(), "ns"),
            ]
        )
        return point_data.sel(time=pd.date_range(range_start, range_end, freq="1H"))

    def _downscale_to_freq(self, point_data: xr.Dataset, freq: Frequency) -> xr.Dataset:
        reindexed = _reindex_to_freq(point_data, freq)

        interpolated: MutableMapping[Hashable, xr.DataArray] = {}
        for key, array in reindexed.items():
            interpolated[key] = self.supported_params[key].interpolate_na(array)

        return reindexed.assign(interpolated)

    def _calculate_output_values(
        self, requested_params: set[str], point_data: xr.Dataset
    ) -> xr.Dataset:
        calculated = {}
        for param in requested_params:
            calculated[param] = self.supported_params[param].calculate(point_data)

        return point_data.assign(calculated)

    def _convert_units(
        self, requested_params: set[str], units: UnitSystem, point_data: xr.Dataset
    ) -> xr.Dataset:
        converted = {}
        for param in requested_params:
            converted[param] = self.supported_params[param].convert_units(
                units, point_data[param]
            )

        return point_data.assign(converted)


def load_index(zarr_s3_path: str) -> xr.Dataset:
    """
    Load the predictions dataset index from storage and convert
    the "time" coord to a pandas DatetimeIndex for later use
    """
    zarr: xr.Dataset = xr.open_zarr(zarr_s3_path)
    zarr["time"] = pd.DatetimeIndex(zarr["time"].values)
    return zarr


def load_latest_dataset(app: Any) -> None:
    """
    Find the latest dataset available. If not already loaded, load it
    and update the application state.
    """
    logging.debug("Attempting to load latest dataset")
    current_timestamp = datetime.now()
    forecast_source: ForecastSource
    forecast_source = DynamoDBForecastSource(
        forecast_table=c.DYNAMODB_FORECAST_TABLE,
        resolution="1x1",
    )

    latest_zarr = forecast_source.get_latest_zarr_path()
    if latest_zarr == app.state.predictions_filename:
        logging.debug("Already loaded %s", latest_zarr)
        return

    app.state.predictions_filename = latest_zarr
    app.state.predictions_dataset = load_index(app.state.predictions_filename)

    # Round current timestamp to the nearest hour
    app.state.FROM_DATE = datetime.combine(
        current_timestamp.date(), time(current_timestamp.hour)
    )
    app.state.TO_DATE = app.state.FROM_DATE + timedelta(hours=48)

    logging.debug("Successfully loaded %s", latest_zarr)


def get_data_service(request: Request) -> DataService:
    """get an instance of the DataService class with pre-loaded dataset"""
    load_latest_dataset(request.app)
    return DataService(request.app.state.predictions_dataset)


def _reindex_to_freq(point_data: xr.Dataset, freq: Frequency) -> xr.Dataset:
    first_time = point_data.coords["time"].min().item()
    last_time = point_data.coords["time"].max().item()
    return point_data.reindex(
        time=pd.date_range(first_time, last_time, freq=freq.value),
    )


def _render_points_geojson(
    parameters: set[str],
    point_data: xr.Dataset,
    requested_feature_ids: list[int | str | None] | None,
) -> dict:
    """render the relevant xarray data as loaded from zarr storage as
    a GeoJSON feature collection"""
    times = [str(time)[:19] + "Z" for time in point_data["time"].values]
    lats = point_data["z"].coords["lat"].values

    # We need to convert longitude back from zarr [0,360) to GeoJSON (-180,180]
    lons = point_data["z"].coords["lon"].values
    lons = longitude_zarr_to_geojson(lons)

    all_values = {}
    for parameter in parameters:
        all_values[parameter] = point_data[parameter].values

    features = []
    feature_seq_id = 0
    for z_index, lon in enumerate(lons):
        for time_index, time_value in enumerate(times):
            feature_seq_id += 1
            props: dict[str, str | float | int | None] = {
                "DATETIME": time_value,
            }
            if (
                requested_feature_ids is not None
                and requested_feature_ids[z_index] is not None
            ):
                props["REQUEST_ID"] = requested_feature_ids[z_index]

            for parameter in parameters:
                props[parameter] = float(
                    all_values[parameter][time_index][z_index].item()
                )

            features.append(
                {
                    "type": "Feature",
                    "id": feature_seq_id,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lats[z_index]],
                    },
                    "properties": props,
                }
            )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def longitude_geojson_to_zarr(lon: np.ndarray) -> np.ndarray:
    """Convert longitude from GeoJSON (-180,180] to the zarr system [0,360)"""
    return np.where(lon < 0, lon + 360.0, lon)


def longitude_zarr_to_geojson(lon: np.ndarray) -> np.ndarray:
    """Convert longitude from the zarr system [0,360) to GeoJSON (-180,180]"""
    return np.where(lon > 180, lon - 360.0, lon)


class ParamNotSupportedError(Exception):
    """One or more requested parameters were not supported by the data service"""

    def __init__(
        self,
        params: Collection[str],
        message: str = "Requested parameters not supported",
    ):
        if params:
            params = list(params)
            params.sort()
        self.params = params
        self.message = message
        super().__init__(self.message)
