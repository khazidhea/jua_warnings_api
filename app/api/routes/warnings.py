"""Warnings API routes"""

from fastapi import Body, Query
from fastapi.routing import APIRouter
from starlette.status import HTTP_200_OK

from app.services.warnings import forcast_service, warnings_service
from app.services.warnings.models import UnitSystem, WarningModel

router = APIRouter(prefix="/warnings", tags=["warnings"])


@router.get(
    "/parameters",
    status_code=HTTP_200_OK,
    summary="Get metadata on all available forecast parameters",
    operation_id="data_get_parameters",
)
def get_parameters(
    units: UnitSystem = Query(
        title="Units",
        default=UnitSystem.DEFAULT,
        example=UnitSystem.DEFAULT,
    ),
) -> dict:
    """Get parameters route"""

    return forcast_service.get_parameters(units)


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
def check_warning():
    """Check warnings route"""

    return warnings_service.check_warnings()
