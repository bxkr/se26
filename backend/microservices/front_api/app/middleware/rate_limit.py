from __future__ import annotations

import jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth.dependencies import ACCESS_TOKEN_COOKIE
from app.auth.security import decode_access_token
from app.config import config

EXEMPT_PATHS = {"/healthz"}


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _identity(request: Request) -> str:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if token:
        try:
            payload = decode_access_token(token)
            return f"user:{payload['sub']}"
        except jwt.InvalidTokenError:
            pass
    return f"ip:{client_ip(request)}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Blanket abuse throttle in front of every route (identified by user id
    once authenticated, IP before that). Login has its own tighter, IP-only
    limit applied in auth_routes.py, since it needs to bite before a session
    — and thus a user identity — exists."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        redis_client = request.app.state.redis_client
        identity = _identity(request)
        over_limit = await redis_client.hit_rate_limit(
            "global",
            identity,
            limit=config.RATE_LIMIT_REQUESTS,
            window_seconds=config.RATE_LIMIT_WINDOW_SECONDS,
        )
        if over_limit:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "too many requests, slow down"}},
            )

        return await call_next(request)
