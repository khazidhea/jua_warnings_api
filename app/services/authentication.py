# pylint: disable=line-too-long
"""
Very simple auth ripped from
https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/
and
https://nilsdebruin.medium.com/fastapi-authentication-revisited-enabling-api-key-authentication-122dc5975680
"""
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

X_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


async def get_api_key(
    api_key: str = Security(X_API_KEY_HEADER),
) -> str:
    """Reads the value of the API key header and validates it"""
    if api_key:
        return api_key
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
    )
