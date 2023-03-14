"""Documentation routes and metadata"""
from typing import TypedDict

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html

from config import get_config

c = get_config()

ROOT_PATH = c.APP_ROOT_PATH
if ROOT_PATH.endswith("/"):
    ROOT_PATH = ROOT_PATH[:-1]

API_DESCRIPTION = """
## What is Jua.ai?

[Jua.ai](https://jua.ai) is a weather forecasting company.

We use machine learning to generate weather predictions more quickly and accurately than contemporary numerical
processing models.

## What can this API provide?

The Jua Forecast API allows developers to fetch a 48 hour weather forecast for one or more points on the globe via
the [/forecast](#operations-forecast-forecast_get_single_point) endpoints.

Various parameters can be specified - e.g. TP (Total precipitation), VAR_2T (2 metre temperature). See the
[/forecast/parameters](#operations-forecast-data_get_parameters) endpoint for more details.

## Contact Us

If you have any questions about the API or its usage, please feel free to reach out to us
at [api-support@jua.ai](mailto:api-support@jua.ai)
"""


class APIMetadata(TypedDict):
    """Simple API Metadata typing"""

    title: str
    description: str
    terms_of_service: str
    contact: dict[str, str]


API_METADATA: APIMetadata = {
    "title": "Jua Forecast API",
    "description": API_DESCRIPTION,
    # pylint: disable=line-too-long
    "terms_of_service": "https://juaai.notion.site/Jua-Customer-terms-f7de139118404f4dadc1624fef2b6f27",
    "contact": {
        "name": "Jua's API team",
        "email": "api-support@jua.ai",
    },
}


router = APIRouter(prefix="/docs", tags=["documentation"])


@router.get("", include_in_schema=False)
def overridden_swagger():
    """Override the swagger UI with our custom styles"""
    return get_swagger_ui_html(
        openapi_url=f"{ROOT_PATH}/docs/openapi.json",
        title="Jua Forecast API",
        swagger_favicon_url=f"{ROOT_PATH}/static/favicon.png",
    )
