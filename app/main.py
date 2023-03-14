"""Module build fastapi app."""

import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

import sentry_sdk
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi_utils.timing import add_timing_middleware
from starlette.responses import RedirectResponse
from starlette.status import HTTP_301_MOVED_PERMANENTLY

from app.api.routes import documentation, forecast, warnings
from app.api.routes.documentation import API_METADATA
from app.services.authentication import get_api_key
from app.services.data_zarr.data_service import load_latest_dataset
from config import get_config

c = get_config()
logging.basicConfig(level=c.LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(c.LOG_LEVEL)

if c.SENTRY_DSN and c.STAGE:
    sentry_sdk.init(
        dsn=c.SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production,
        traces_sample_rate=1.0,
        environment=c.STAGE,
    )

ROOT_PATH = c.APP_ROOT_PATH
if ROOT_PATH.endswith("/"):
    ROOT_PATH = ROOT_PATH[:-1]

V1_PREFIX = "/v1"

DOCS_PREFIX = documentation.router.prefix

app = FastAPI(
    root_path=ROOT_PATH,
    openapi_url=None,
    **API_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load initial zarr prediction data
app.state.predictions_filename = None


# Setup middleware and routes


@app.middleware("http")
async def add_dataset_file_header(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Add the dataset filename (from S3/DynamoDB) in a header if present"""
    response = await call_next(request)
    if app.state.predictions_filename:
        response.headers["X-Dataset"] = Path(app.state.predictions_filename).name
    return response


add_timing_middleware(app, record=logger.info, prefix="app", exclude="untimed")


@app.get("/", include_in_schema=False)
def index() -> Response:
    """Redirect to docs page to avoid 404 or 500s"""
    return RedirectResponse(f"{ROOT_PATH}/docs", status_code=HTTP_301_MOVED_PERMANENTLY)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(
    forecast.router,
    prefix=V1_PREFIX
    # forecast.router, prefix=V1_PREFIX, dependencies=[Depends(get_api_key)]
)
app.include_router(warnings.router, prefix=V1_PREFIX)
app.include_router(documentation.router)


@app.get(f"{DOCS_PREFIX}/openapi.json", include_in_schema=False)
def overridden_openapi() -> dict[str, Any]:
    """
    Manually serve the openapi.json file so that it respects ROOT_PATH
    /docs is used as a prefix as it doesn't require an API key to access
    """
    # TODO: show dynamic API version # pylint: disable=fixme

    servers = []
    if ROOT_PATH:
        servers.append({"url": ROOT_PATH})

    return get_openapi(
        title="Jua Forecast API",
        version="0.1.0",
        routes=app.routes,
        servers=servers,
        description=API_METADATA["description"],
    )


load_latest_dataset(app)
print("hello")

if __name__ == "__main__":
    # Run locally with automatic reloading
    import uvicorn

    load_latest_dataset(app)

    uvicorn.run("app.main:app", port=8000, reload=True, access_log=False)
