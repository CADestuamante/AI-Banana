"""Authentication service.

Credentials are stored as SHA-256 hashes in a local JSON file
(configs/users.json).  On first run the file is created with two
default accounts so the application is usable out of the box.

Default credentials
-------------------
  operator / operator123   (Role.OPERATOR)
  admin    / admin123      (Role.MANAGER)

Production deployments should change these passwords immediately
and ideally replace this module with a proper identity provider.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from banana_ai.auth.models import Role, User

logger = logging.getLogger(__name__)

_DEFAULT_USERS = [
    {"username": "operator", "password_hash": "", "role": "operator"},
    {"username": "admin",    "password_hash": "", "role": "manager"},
]

_DEFAULT_PASSWORDS = {
    "operator": "operator123",
    "admin":    "admin123",
}

_USERS_FILE = Path("configs/users.json")


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _ensure_users_file() -> None:
    """Create users.json with defaults if it does not exist."""
    if _USERS_FILE.exists():
        return
    _USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for entry in _DEFAULT_USERS:
        records.append({
            "username":      entry["username"],
            "password_hash": _hash(_DEFAULT_PASSWORDS[entry["username"]]),
            "role":          entry["role"],
        })
    _USERS_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    logger.info("Created default users file at %s", _USERS_FILE)


def _load_users() -> list[dict]:
    _ensure_users_file()
    return json.loads(_USERS_FILE.read_text(encoding="utf-8"))


def login(username: str, password: str) -> Optional[User]:
    """Return a User if credentials are valid, otherwise None."""
    users = _load_users()
    pw_hash = _hash(password)
    for record in users:
        if record["username"] == username and record["password_hash"] == pw_hash:
            try:
                role = Role(record["role"])
            except ValueError:
                logger.warning("Unknown role '%s' for user '%s'", record["role"], username)
                return None
            logger.info("User '%s' logged in as %s", username, role.value)
            return User(username=username, role=role)
    logger.warning("Failed login attempt for username '%s'", username)
    return None


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """Change a user's password.  Returns True on success."""
    users = _load_users()
    old_hash = _hash(old_password)
    for record in users:
        if record["username"] == username and record["password_hash"] == old_hash:
            record["password_hash"] = _hash(new_password)
            _USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")
            logger.info("Password changed for user '%s'", username)
            return True
    return False