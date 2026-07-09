from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth.dependencies import ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, get_current_user
from app.auth.security import create_access_token, new_refresh_jti, verify_password
from app.config import config
from app.schemas import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "message": message}})


def _set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=config.ACCESS_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=config.REFRESH_TOKEN_TTL_SECONDS,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path="/")


async def _issue_tokens(request: Request, response: Response, *, user_id: str, username: str, role: str) -> None:
    access_token = create_access_token(user_id=user_id, username=username, role=role)
    refresh_jti = new_refresh_jti()
    await request.app.state.redis_client.store_refresh_token(
        refresh_jti, user_id, ttl=config.REFRESH_TOKEN_TTL_SECONDS
    )
    _set_auth_cookies(response, access_token=access_token, refresh_token=refresh_jti)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    postgres = request.app.state.postgres_client
    row = await postgres.get_user_by_username(payload.username)
    if row is None or not row["is_active"] or not verify_password(payload.password, row["password_hash"]):
        raise _unauthorized("invalid username or password")

    await _issue_tokens(request, response, user_id=str(row["id"]), username=row["username"], role=row["role"])
    return {"user": {"id": str(row["id"]), "username": row["username"], "role": row["role"]}}


@router.post("/refresh")
async def refresh(request: Request, response: Response) -> dict:
    refresh_jti = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_jti:
        raise _unauthorized("missing refresh token")

    redis_client = request.app.state.redis_client
    user_id = await redis_client.get_refresh_token_owner(refresh_jti)
    if user_id is None:
        raise _unauthorized("refresh token expired or revoked")

    postgres = request.app.state.postgres_client
    row = await postgres.get_user_by_id(user_id)
    if row is None or not row["is_active"]:
        await redis_client.revoke_refresh_token(refresh_jti)
        raise _unauthorized("user no longer active")

    await redis_client.revoke_refresh_token(refresh_jti)
    await _issue_tokens(request, response, user_id=str(row["id"]), username=row["username"], role=row["role"])
    return {"user": {"id": str(row["id"]), "username": row["username"], "role": row["role"]}}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    refresh_jti = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if refresh_jti:
        await request.app.state.redis_client.revoke_refresh_token(refresh_jti)
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": user}
