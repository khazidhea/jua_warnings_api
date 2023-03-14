"""Forecast API routes"""

from fastapi import Depends, HTTPException, Query, Request
from fastapi.routing import APIRouter
from pydantic import Required
from starlette.status import HTTP_200_OK

from app.api.routes.schemas import (
    FeatureCollectionRequest,
    FeatureCollectionResponse,
    Parameter,
    ParameterDetails,
    ParameterDetailsResponse,
)
from app.api.routes.utils import parse_parameters
from app.services.data_zarr.data_service import (
    DataService,
    ParamNotSupportedError,
    get_data_service,
)
from app.services.data_zarr.params import Frequency, UnitSystem

router = APIRouter(prefix="/forecast", tags=["forecast"])


GET_SINGLE_POINT_DESCRIPTION = """
Get forecast data for a single point for selected parameters.

A list of available parameters and their units is available at the
/api/data/parameters endpoint.

The response is a valid GeoJSON FeatureCollection object.
Every prediction timestep is an individual Feature with the corresponding
closest Point in our dataset.

Predictions are calculated from the current time for the next 48 hours,
in n-minute increments.

If the "id" field is set on an input Feature, the prediction data corresponding to
that feature will have the REQUEST_ID property set to the same value.

**Notes:**
* The coordinates of the returned points might differ from the requested coordinates - we return the nearest point available
* Every timestamp is returned as a separate point (at the same coordinates)
* The timestamp is returned in the `DATETIME` property of the feature as an ISO8601-formatted date/time
* All coordinates are assumed to be in WGS-84
"""


@router.get(
    "",
    status_code=HTTP_200_OK,
    summary="Get forecast data for a single point",
    description=GET_SINGLE_POINT_DESCRIPTION,
    operation_id="forecast_get_single_point",
    response_model=FeatureCollectionResponse,
)
def get_single_point(
    request: Request,
    lon: float = Query(
        title="Longitude", default=Required, example="-69.99", ge=-180, le=180
    ),
    lat: float = Query(
        title="Latitude", default=Required, example="0.0", ge=-90, le=90
    ),
    parameters: str = Query(
        alias="parameters",
        example="VAR_2T,TP",
        default="VAR_2T,TP",
        description="Dataset parameters",
        max_length=200,
    ),
    units: UnitSystem = Query(
        title="Units",
        default=UnitSystem.DEFAULT,
        example=UnitSystem.DEFAULT,
    ),
    freq: Frequency = Query(
        title="Units",
        default=Frequency.ONE_HOUR,
        example=Frequency.ONE_HOUR,
    ),
    data_service: DataService = Depends(get_data_service),
) -> dict:
    """Retrieve forecast data at the provided coordinates."""

    requested_params = parse_parameters(parameters)

    try:
        return data_service.get_points_as_geojson(
            coords=[(lon, lat)],
            date_range=(request.app.state.FROM_DATE, request.app.state.TO_DATE),
            requested_params=requested_params,
            units=units,
            freq=freq,
        )
    except ParamNotSupportedError as err:
        raise HTTPException(
            status_code=400, detail=f"Parameters not supported: {', '.join(err.params)}"
        ) from err


GET_MULTIPLE_POINTS_DESCRIPTION = """
Get forecast data for multiple points for selected parameters.

A list of available parameters and their units is available at the
/api/data/parameters endpoint.

The response is a valid GeoJSON FeatureCollection object.
Every prediction timestep is an individual Feature with the corresponding
closest Point in our dataset.

Predictions are calculated from the current time for the next 48 hours,
in 5-minute increments.

If the "id" field is set on an input Feature, the prediction data corresponding to
that feature will have the REQUEST_ID property set to the same value.

**Notes:**
* The coordinates of the returned points might differ from the requested coordinates - we return the nearest point available
* Every timestamp is returned as a separate point (at the same coordinates)
* The timestamp is returned in the `DATETIME` property of the feature as an ISO8601-formatted date/time
* All coordinates are assumed to be in WGS-84
"""


@router.post(
    "",
    status_code=HTTP_200_OK,
    summary="Get forecast data for multiple points",
    description=GET_MULTIPLE_POINTS_DESCRIPTION,
    operation_id="forecast_get_multiple_points",
    response_model=FeatureCollectionResponse,
)
def get_multiple_points(
    request: Request,
    body: FeatureCollectionRequest,
    parameters: str = Query(
        alias="parameters",
        example="VAR_2T,TP",
        default="VAR_2T,TP",
        description="Dataset parameters",
        max_length=200,
    ),
    units: UnitSystem = Query(
        title="Units",
        default=UnitSystem.DEFAULT,
        example=UnitSystem.DEFAULT,
    ),
    freq: Frequency = Query(
        title="Frequency",
        default=Frequency.ONE_HOUR,
        example=Frequency.ONE_HOUR,
    ),
    data_service: DataService = Depends(get_data_service),
) -> dict:
    """Retrieve forecast data for all points in the submitted GeoJSON
    feature collection."""

    requested_params = parse_parameters(parameters)

    coords = [feature.geometry.coordinates for feature in body.features]
    ids = [feature.id for feature in body.features]

    try:
        return data_service.get_points_as_geojson(
            coords=coords,
            date_range=(request.app.state.FROM_DATE, request.app.state.TO_DATE),
            requested_params=requested_params,
            requested_feature_ids=ids,
            units=units,
            freq=freq,
        )
    except ParamNotSupportedError as err:
        raise HTTPException(
            status_code=400, detail=f"Parameters not supported: {', '.join(err.params)}"
        ) from err


GET_PARAMETERS_DESCRIPTION = """
Fetch an object containing metadata on all available forecast parameters.
Every key of this object is a parameter and represents how that parameter
is referenced to in other endpoints.

Every parameter has a corresponding object that contains further details,
such as the long name of the parameter, its description, ISO unit and more.

Note: Not all details are guaranteed to be present for every parameter.
"""


@router.get(
    "/parameters",
    status_code=HTTP_200_OK,
    response_model=ParameterDetailsResponse | dict[Parameter, ParameterDetails],
    summary="Get metadata on all available forecast parameters",
    description=GET_PARAMETERS_DESCRIPTION,
    operation_id="data_get_parameters",
)
def get_parameters(
    units: UnitSystem = Query(
        title="Units",
        default=UnitSystem.DEFAULT,
        example=UnitSystem.DEFAULT,
    ),
    data_service: DataService = Depends(get_data_service),
) -> dict:
    """Get parameters route"""

    return data_service.get_parameters(units)
