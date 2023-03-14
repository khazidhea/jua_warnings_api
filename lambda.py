"""Module wrap fastapi with Magnum to run in lambda."""

from mangum import Mangum

from app.main import app
from app.services.data_zarr.data_service import load_latest_dataset

handler = Mangum(app)

load_latest_dataset(app)
