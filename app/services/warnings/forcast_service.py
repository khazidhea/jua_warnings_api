"""Module service working with forcast api."""

import json
from datetime import timezone

import requests
from dateutil import parser

from app.services.warnings.models import UnitSystem
from config import get_config

c = get_config()


def get_parameters(units: UnitSystem):
    """get parameter list"""

    url = f"{c.FORFACT_API_URL}v1/forecast/parameters"
    params = {"units": units.value.lower()}
    headers = {"x-api-key": c.FORFACT_API_KEY}
    response = requests.get(url, params=params, headers=headers, timeout=60)
    return response.json()


def convert_forcast_data(data: dict):
    """Convert zarr data to the following format:
    "2023-03-14 04:00:00+00:00": {
        "71.42916665688892": {
            "51.1291666681783": {
                "DATETIME": "2023-03-14T04:00:00Z",
                "VAR_10U": -0.4781881272792816
            }
        },
        "76.94583332334105": {
            "43.23750000181853": {
                "DATETIME": "2023-03-14T04:00:00Z",
                "VAR_10U": 0.44463953375816345
            }
        }
    }
    """

    result: dict = {}
    features = data["features"]
    for item in features:
        coords = item["geometry"]["coordinates"]
        properties = item["properties"]
        warning_datetime = properties["DATETIME"]
        warning_datetime = parser.parse(warning_datetime).replace(tzinfo=timezone.utc)

        if str(warning_datetime) not in result:
            result[str(warning_datetime)] = {}

        if coords[0] not in result[str(warning_datetime)]:
            result[str(warning_datetime)][coords[0]] = {}

        result[str(warning_datetime)][coords[0]][coords[1]] = properties

    return result


def get_forcast_data(parameters, coordinates):
    """Load forcast data to check alerts:"""

    url = f"{c.FORFACT_API_URL}v1/forecast"
    headers = {"x-api-key": c.FORFACT_API_KEY}
    params = {"parameters": parameters, "format": "geojson"}
    data = {"type": "FeatureCollection", "features": []}
    for coord in coordinates:
        data["features"].append(
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": coord}}
        )
    response = requests.post(
        url=url, params=params, data=json.dumps(data), headers=headers, timeout=60
    )
    data = response.json()
    return convert_forcast_data(data)
