"""
backend/routers/auth.py — register, login, logout, me
"""
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.auth_utils import (
    create_session,
    hash_password,
    require_auth,
    verify_password,
)
from backend.db import get_conn

router = APIRouter()


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/api/auth/register")
def register(req: AuthRequest):
    username = req.username.strip().lower()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, hash_password(req.password), int(time.time())),
        )
        conn.commit()

    token = create_session(user_id)
    return {"success": True, "token": token, "username": username, "user_id": user_id}


@router.post("/api/auth/login")
def login(req: AuthRequest):
    username = req.username.strip().lower()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_session(row["id"])
    return {"success": True, "token": token, "username": username, "user_id": row["id"]}


@router.post("/api/auth/logout")
def logout(authorization: str = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        with get_conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
    return {"success": True}


@router.get("/api/auth/me")
def me(user: dict = Depends(require_auth)):
    return {"user_id": user["user_id"], "username": user["username"]}
