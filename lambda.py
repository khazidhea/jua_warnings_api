"""Module wrap fastapi with Magnum to run in lambda."""

from mangum import Mangum

from app.main import app

handler = Mangum(app)
