"""Data parameter registry"""

# pylint: disable=too-many-instance-attributes

from enum import Enum
from typing import Callable, Hashable, KeysView, Mapping

import xarray as xr
from pint import Quantity as Q_

from app.services.data_zarr.calculations import (
    calc_wind_direction,
    calc_wind_speed,
    interp_bfill_average,
    interp_linear,
    lookup,
)


class UnitSystem(Enum):
    """A system of units"""

    SI = "SI"
    DEFAULT = "DEFAULT"


class Frequency(Enum):
    """A frequency of dataset datetime"""

    FIVE_MINUTE = "5min"
    ONE_HOUR = "1H"


class ParameterSpec:
    """A parameter spec"""

    short_name: str
    long_name: str
    data_unit: str
    units: dict[UnitSystem, str]
    data_keys: set[str]
    interpolate_na: Callable[[xr.DataArray], xr.DataArray]
    calculate: Callable[[xr.Dataset], xr.DataArray]

    def __init__(
        self,
        short_name: str,
        long_name: str,
        data_unit: str,
        si_unit: str,
        default_unit: str,
        data_keys: set[str] | None = None,
        interpolator: Callable[[xr.DataArray], xr.DataArray] = interp_linear,
        calculator: Callable[[xr.Dataset], xr.DataArray] | None = None,
    ):  # pylint: disable=[too-many-arguments]
        """Instantiate a ParameterSpec"""
        self.short_name = short_name
        self.long_name = long_name
        self.data_unit = data_unit
        self.units = {
            UnitSystem.SI: si_unit,
            UnitSystem.DEFAULT: default_unit,
        }
        self.default_unit = default_unit
        self.data_keys = data_keys if data_keys else {short_name}
        self.interpolate_na = interpolator
        self.calculate = calculator if calculator else lookup(list(self.data_keys)[0])

    def keys_present(self, keys: KeysView[str]) -> bool:
        """Check that all of the required keys for this parameter are available"""
        return self.data_keys.issubset(keys)

    def convert_units(self, units: UnitSystem, data: xr.DataArray) -> xr.DataArray:
        """Convert the data values to the target unit system"""
        if self.data_unit == self.units[units]:
            return data

        return xr.DataArray(
            Q_(data.to_numpy(), self.data_unit).to(self.units[units]).magnitude,
            coords=data.coords,
            dims=data.dims,
            name=data.name,
        )

    def to_json(self, units: UnitSystem) -> dict[str, str]:
        """Render a json-like dict containing the metadata for this parameter"""
        return {
            "short_name": self.short_name,
            "long_name": self.long_name,
            "units": self.units[units],
        }


INTERPOLATED_STEPS_PER_HOUR = 60 / 5  # We downscale to 5min steps

SUPPORTED_PARAMETERS = {
    "VAR_10U": ParameterSpec(
        short_name="VAR_10U",
        long_name="10 metre U wind component",
        data_unit="m s**-1",
        si_unit="m s**-1",
        default_unit="m s**-1",
    ),
    "VAR_10V": ParameterSpec(
        short_name="VAR_10V",
        long_name="10 metre V wind component",
        data_unit="m s**-1",
        si_unit="m s**-1",
        default_unit="m s**-1",
    ),
    "VAR_2T": ParameterSpec(
        short_name="VAR_2T",
        long_name="2 metre temperature",
        data_unit="K",
        si_unit="K",
        default_unit="degC",
    ),
    "TCWV": ParameterSpec(
        short_name="TCWV",
        long_name="total column water vapour",
        data_unit="kg m**-2",
        si_unit="kg m**-2",
        default_unit="kg m**-2",
    ),
    "SP": ParameterSpec(
        short_name="SP",
        long_name="surface pressure",
        data_unit="Pa",
        si_unit="Pa",
        default_unit="hPa",
    ),
    "MSL": ParameterSpec(
        short_name="MSL",
        long_name="mean sea level pressure",
        data_unit="Pa",
        si_unit="Pa",
        default_unit="hPa",
    ),
    "TP": ParameterSpec(
        short_name="TP",
        long_name="total precipitation",
        data_unit="m",
        si_unit="m",
        default_unit="mm",
        interpolator=interp_bfill_average(INTERPOLATED_STEPS_PER_HOUR),
    ),
    "10WS": ParameterSpec(
        short_name="10WS",
        long_name="10 metre wind speed",
        data_unit="m s**-1",
        si_unit="m s**-1",
        default_unit="m s**-1",
        data_keys={"VAR_10U", "VAR_10V"},
        calculator=lambda data: calc_wind_speed(data["VAR_10U"], data["VAR_10V"]),
    ),
    "10WD": ParameterSpec(
        short_name="10WD",
        long_name="10 metre wind direction",
        data_unit="degree",
        si_unit="degree",
        default_unit="degree",
        data_keys={"VAR_10U", "VAR_10V"},
        calculator=lambda data: calc_wind_direction(data["VAR_10U"], data["VAR_10V"]),
    ),
}


def gen_supported_params(dataset: xr.Dataset) -> Mapping[Hashable, ParameterSpec]:
    """Get the map of supported parameters"""
    available_keys = dataset.data_vars.keys()
    return {
        k: v for k, v in SUPPORTED_PARAMETERS.items() if v.keys_present(available_keys)
    }
