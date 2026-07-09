from __future__ import annotations

from typing import Any

import jwt
from fastapi import HTTPException, Request

from app.auth.security import decode_access_token

ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": message}})


def _forbidden(message: str) -> HTTPException:
    return HTTPException(status_code=403, detail={"error": {"code": "FORBIDDEN", "message": message}})


async def get_current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise _unauthorized("not authenticated")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("access token expired") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("invalid access token") from None
    return {"id": payload["sub"], "username": payload["username"], "role": payload["role"]}


async def require_admin(request: Request) -> dict[str, Any]:
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise _forbidden("admin role required")
    return user
