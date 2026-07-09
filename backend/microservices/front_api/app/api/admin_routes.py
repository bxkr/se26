from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import require_admin
from app.auth.security import hash_password
from app.clients.postgres_client import UsernameTakenError, UserNotFoundError
from app.schemas import PasswordReset, UserCreate, UserUpdate

router = APIRouter(prefix="/admin/users", tags=["admin"], dependencies=[Depends(require_admin)])


def _validation_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"error": {"code": "VALIDATION_ERROR", "message": message}})


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": message}})


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"error": {"code": "CONFLICT", "message": message}})


@router.get("")
async def list_users(request: Request) -> dict:
    users = await request.app.state.postgres_client.list_users()
    return {"users": users}


@router.post("")
async def create_user(payload: UserCreate, request: Request) -> dict:
    if payload.role not in ("user", "admin"):
        raise _validation_error("Field 'role' must be 'user' or 'admin'")
    if not payload.username or not payload.password:
        raise _validation_error("Fields 'username' and 'password' are required")

    postgres = request.app.state.postgres_client
    try:
        user = await postgres.create_user(
            username=payload.username, password_hash=hash_password(payload.password), role=payload.role
        )
    except UsernameTakenError:
        raise _conflict(f"username already taken: {payload.username}") from None
    return {"user": user}


@router.patch("/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, request: Request) -> dict:
    if payload.role is not None and payload.role not in ("user", "admin"):
        raise _validation_error("Field 'role' must be 'user' or 'admin'")

    postgres = request.app.state.postgres_client
    try:
        user = await postgres.update_user(user_id, role=payload.role, is_active=payload.is_active)
    except UserNotFoundError:
        raise _not_found(f"unknown user_id: {user_id}") from None
    return {"user": user}


@router.delete("/{user_id}")
async def delete_user(user_id: str, request: Request) -> dict:
    postgres = request.app.state.postgres_client
    try:
        await postgres.delete_user(user_id)
    except UserNotFoundError:
        raise _not_found(f"unknown user_id: {user_id}") from None
    return {"status": "ok"}


@router.post("/{user_id}/reset-password")
async def reset_password(user_id: str, payload: PasswordReset, request: Request) -> dict:
    if not payload.new_password:
        raise _validation_error("Field 'new_password' is required")

    postgres = request.app.state.postgres_client
    try:
        await postgres.set_password_hash(user_id, hash_password(payload.new_password))
    except UserNotFoundError:
        raise _not_found(f"unknown user_id: {user_id}") from None
    return {"status": "ok"}
