"""Warnings API routes"""

import boto3
from fastapi import Body, Depends, Query, Request
from fastapi.routing import APIRouter
from starlette.status import HTTP_200_OK

from app.api.routes.schemas import Parameter, ParameterDetails, ParameterDetailsResponse
from app.services.data_zarr.data_service import DataService, get_data_service
from app.services.data_zarr.params import UnitSystem
from app.services.warnings import warnings_service
from app.services.warnings.warning import WarningModel

router = APIRouter(prefix="/warnings", tags=["warnings"])


@router.get(
    "/parameters",
    status_code=HTTP_200_OK,
    response_model=ParameterDetailsResponse | dict[Parameter, ParameterDetails],
    summary="Get metadata on all available forecast parameters",
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


@router.get(
    "",
    status_code=HTTP_200_OK,
    summary="Get warning list",
)
def get_warnings():
    """Get warnings route"""
    return warnings_service.get_warnings()


@router.post(
    "",
    status_code=HTTP_200_OK,
    summary="Create warning",
)
def add_warning(payload: WarningModel = Body(...)):
    """Put warning item into dynamodb"""

    warnings_service.add_warning(warning=payload)


@router.delete(
    "/delete_all",
    status_code=HTTP_200_OK,
    summary="Delete all warnings",
)
def delete_warnings():
    """Delete warnings route"""
    return warnings_service.delete_all()


@router.get(
    "/check_warnings",
    status_code=HTTP_200_OK,
    summary="Check warnings",
)
def check_warning(
    request: Request, data_service: DataService = Depends(get_data_service)
):
    return warnings_service.check_warnings(
        data_service=data_service,
        date_range=(request.app.state.FROM_DATE, request.app.state.TO_DATE),
    )
