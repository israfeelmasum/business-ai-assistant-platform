"""Rate limiting middleware — per API key throttling."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def get_rate_limit_key(request: Request) -> str:
    """Use API key as rate limit key, fallback to IP address."""
    api_key = request.headers.get("x-api-key")
    return api_key if api_key else get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)
