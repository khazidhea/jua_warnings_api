"""Calculations for the various parameters"""

from typing import Callable

import xarray as xr
from metpy.calc import wind_direction, wind_speed
from metpy.units import units

m = units.meter
s = units.second


def lookup(key: str) -> Callable[[xr.Dataset], xr.DataArray]:
    """A simple lookup function for parameters that don't require any calculation"""
    return lambda data: data[key]


def interp_bfill_average(
    interpolated_steps: float,
) -> Callable[[xr.DataArray], xr.DataArray]:
    """Interpolate na values to 5min for data like total precipitation"""
    return lambda data: (data / interpolated_steps).bfill(dim="time")


def interp_linear(data: xr.DataArray) -> xr.DataArray:
    """Interpolate na values with linear method along time dimension"""
    return data.interpolate_na(dim="time", method="linear")


def calc_wind_direction(
    u_component: xr.DataArray, v_component: xr.DataArray
) -> xr.DataArray:
    """Calculate the wind direction from the U and V components"""
    return wind_direction(u_component * m / s, v_component * m / s)


def calc_wind_speed(
    u_component: xr.DataArray, v_component: xr.DataArray
) -> xr.DataArray:
    """Calculate the wind speed from the U and V components"""
    return wind_speed(u_component * m / s, v_component * m / s)
