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

    WARNINGS_TABLE: str = Field("warnings-table", env="WARNINGS_TABLE")
    WARNINGS_HISTORY_TABLE: str = Field(
        "warnings_history", env="WARNINGS_HISTORY_TABLE")
    FORFACT_API_URL: str = Field("https://api.jua.ai/", env="FORFACT_API_URL")
    FORFACT_API_KEY: str = Field(
        "WVKfcSO0DC8n78tJkF3DoBJP2NmPtoD529cciSlj", env="FORFACT_API_KEY"
    )

    check_expiration = True
    jwt_header_prefix = "Bearer"
    jwt_header_name = "Authorization"
    userpools = {
        "us": {
            "region": "us-east-1",
            "userpool_id": "us-east-1_al0VMUMT5",
            "app_client_id": "6kbd7bg0hs0c5v5uu9nvldqqav",
        },
    }

    GOOGLE_CLIENT_ID: str = Field(
        "1011339696135-4r1ovkcr4iios2pe7jidpmcek6f3m4lf.apps.googleusercontent.com",
        env="GOOGLE_CLIENT_ID",
    )
    GOOGLE_SECRET: str = Field(
        "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", env="GOOGLE_SECRET"
    )

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
