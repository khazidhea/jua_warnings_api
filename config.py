"""Configuration for CDK stack"""

from pydantic import BaseSettings, Field


class GlobalConfig(BaseSettings):
    """Global configurations.
    Inspired by
    https://rednafi.github.io/digressions/python/2020/06/03/python-configs.html"""

    APP_NAME: str = "warning-api"
    APP_ROOT_PATH: str = Field("/", env="APP_ROOT_PATH")
    STAGE: str = Field("dev", env="STAGE")
    SENTRY_DSN: str = Field("", env="SENTRY_DSN")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")

    DYNAMODB_FORECAST_TABLE: str = Field(
        "forecast-releases-prod", env="DYNAMODB_FORECAST_TABLE"
    )

    WARNINGS_TABLE: str = Field(f"warnings-table", env="WARNINGS_TABLE")

    @property
    def full_name(self) -> str:
        """return the full name of the stack"""
        return f"{self.APP_NAME}-{self.STAGE}"

    @property
    def is_prod(self) -> bool:
        """True if the current stage is prod"""
        return self.STAGE == "prod"

    @property
    def is_stage(self) -> bool:
        """True if the current stage is stage"""
        return self.STAGE == "stage"


class BranchConfig(GlobalConfig):
    """Branch configurations."""

    APP_ROOT_PATH: str = "/"


class StageConfig(GlobalConfig):
    """Staging configurations."""


class ProdConfig(GlobalConfig):
    """Production configurations."""


class FactoryConfig:
    """Returns a config instance depending on the STAGE variable."""

    def __init__(self, stage: str | None):
        self.stage = stage

    def __call__(self) -> GlobalConfig:
        if self.stage == "prod":
            return ProdConfig()

        if self.stage == "stage":
            return StageConfig()

        return BranchConfig()


def get_config() -> GlobalConfig:
    """Retrieve a config instance"""
    return FactoryConfig(GlobalConfig().STAGE)()
