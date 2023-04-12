from typing import Optional

from fastapi_cognito import CognitoAuth, CognitoSettings, CognitoToken

from config import get_config

c = get_config()


class CustomTokenModel(CognitoToken):
    sub: str
    origin_jti: Optional[str]


settings = CognitoSettings.from_global_settings(c)
settings.custom_cognito_token_model = CustomTokenModel

cognito_us = CognitoAuth(settings=settings, userpool_name="us")
