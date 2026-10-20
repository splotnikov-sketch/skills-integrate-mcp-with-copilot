"""Teacher credentials and short-lived, server-side sessions."""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

TEACHERS_FILE = Path(__file__).with_name("teachers.json")
ITERATIONS = 600_000
SESSION_SECONDS = 3600
sessions: dict[str, tuple[str, float]] = {}
bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def password_record(password: str) -> dict[str, str]:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), ITERATIONS
    ).hex()
    return {"salt": salt, "password_hash": digest}


def authenticate(username: str, password: str) -> bool:
    path = Path(os.environ.get("TEACHERS_FILE", str(TEACHERS_FILE)))
    try:
        teachers = json.loads(path.read_text())
        if not isinstance(teachers, dict):
            raise ValueError("Teacher file must contain an object")
        for record in teachers.values():
            if not isinstance(record, dict):
                raise ValueError("Invalid teacher record")
            salt = record["salt"]
            digest = record["password_hash"]
            if (not isinstance(salt, str) or not isinstance(digest, str)
                    or len(bytes.fromhex(salt)) != 16
                    or len(bytes.fromhex(digest)) != 32):
                raise ValueError("Invalid password hash")
    except (OSError, ValueError, KeyError, TypeError):
        logger.exception("Unable to load teacher credentials")
        raise HTTPException(503, "Teacher login is unavailable. Contact the administrator.")

    # Use the same password work even when the username is unknown.
    record = teachers.get(username, {"salt": "00" * 16, "password_hash": "00" * 32})
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(record["salt"]), ITERATIONS
    ).hex()
    return hmac.compare_digest(digest, record["password_hash"]) and username in teachers


def create_session(username: str) -> str:
    now = time.monotonic()
    for token, (_, expires) in list(sessions.items()):
        if expires <= now:
            sessions.pop(token, None)
    token = secrets.token_urlsafe(32)
    sessions[token] = (username, now + SESSION_SECONDS)
    return token


def require_teacher(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    token = credentials.credentials if credentials else ""
    session = sessions.get(token)
    if session is None or session[1] <= time.monotonic():
        sessions.pop(token, None)
        raise HTTPException(
            401, "Teacher login required", headers={"WWW-Authenticate": "Bearer"}
        )
    return token
