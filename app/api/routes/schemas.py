"""Pydantic models"""


from typing import Literal

from pydantic import BaseModel, Field


class PointGeometry(BaseModel):
    """A GeoJSON geometry of type Point with coordinates in WGS-84"""

    type: str = Field("Point", const=True)
    coordinates: tuple[float, float]


class Feature(BaseModel):
    """A GeoJSON feature with point geometry"""

    type: str = Field("Feature", const=True)
    id: int | str | None = None
    geometry: PointGeometry
    properties: dict[str, float | int | str | None] = Field(default_factory=dict)


class FeatureCollection(BaseModel):
    """A GeoJSON feature collection with point geometries only"""

    type: str = Field("FeatureCollection", const=True)
    features: list[Feature]


class FeatureCollectionRequest(FeatureCollection):
    """
    A GeoJSON FeatureCollection. Note that the properties object is not required.
    """

    class Config:
        """
        Model config
        A separate class is used here to add a separate example for the request.
        """

        schema_extra = {
            "example": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-70, 0]},
                    },
                    {
                        "type": "Feature",
                        "id": 1,
                        "geometry": {"type": "Point", "coordinates": [-23, 84.5]},
                    },
                ],
            }
        }


class FeatureCollectionResponse(FeatureCollection):
    """
    A valid GeoJSON FeatureCollection.
    The response contains the requested forecast parameters as properties on each
    Feature.
    """

    class Config:
        """
        Model config
        A separate class is used here to document the example response.
        """

        schema_extra = {
            "example": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "id": 1,
                        "geometry": {"type": "Point", "coordinates": [-70, 0]},
                        "properties": {
                            "DATETIME": "2021-01-01T00:00:00Z",
                            "VAR_2T": 298.6087646484375,
                            "TP": 0.000005424022674560547,
                        },
                    },
                    {
                        "type": "Feature",
                        "id": 2,
                        "geometry": {"type": "Point", "coordinates": [-23, 84.5]},
                        "properties": {
                            "REQUEST_ID": 1,
                            "DATETIME": "2021-01-01T00:05:00Z",
                            "VAR_2T": 298.56984456380206,
                            "TP": 0.000053625864287217454,
                        },
                    },
                ],
            }
        }


Parameter = Literal[
    "10WD",
    "10WS",
    "MSL",
    "SP",
    "TCWV",
    "TP",
    "VAR_10U",
    "VAR_10V",
    "VAR_2T",
]


class PredictionDataResponse(BaseModel):
    """Response object for point data"""

    loc: list[int | float] = Field(
        description="A lon/lat pair", max_items=2, min_items=2
    )
    data: dict[str, dict[str, float]] = Field(
        description=(
            "A series of predictions. "
            'Every key is a datetime of the format "2021-01-01_00:00:00"'
        )
    )

    class Config:
        """Model config"""

        schema_extra = {
            "example": {
                "loc": [-69.99, 0],
                "data": {
                    "2021-01-01_00:00:00": {
                        "VAR_2T": 299.5013427734375,
                        "TP": 0.0000629425048828125,
                    },
                    "2021-01-01_01:00:00": {
                        "VAR_2T": 299.3760986328125,
                        "TP": 0.00008247420191764832,
                    },
                },
            }
        }


class ParameterDetails(BaseModel):
    """
    Metadata for a forecast parameter
    """

    short_name: str
    long_name: str
    units: str


class ParameterDetailsResponse(BaseModel):
    """
    A response containing metadata for all available forecast parameters.
    """

    class Config:
        """
        Model config
        extra=forbid with an empty class prevents this class ever being instantiated
        it is used only for its example
        This is a bit of a hack to get the example to show in the API schema.
        The schema doesn't work correctly when the response is like `dict[str, Model]`
        """

        extra = "forbid"
        schema_extra = {
            "example": {
                "TP": {
                    "short_name": "TP",
                    "long_name": "Total precipitation",
                    "units": "m",
                },
                "VAR_2T": {
                    "short_name": "VAR_2T",
                    "long_name": "2 metre temperature",
                    "units": "K",
                },
            }
        }
