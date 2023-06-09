from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class UnitSystem(Enum):
    """A system of units"""

    SI = "SI"
    DEFAULT = "DEFAULT"


class Condition(Enum):
    """A warning condition"""

    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_THAN_E = "GREATER_THAN_E"
    LESS_THAN_E = "LESS_THAN_E"


class WarningModel(BaseModel):
    """A warning model"""

    name: str
    location: str
    email: str
    parameter: str
    condition: Condition
    warning_datetime: datetime
    value: float
    coordinates: tuple[float, float]
    phone_number: str
    before_6: bool
    before_12: bool
    before_48: bool
