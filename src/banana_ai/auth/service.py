"""Authentication service — dùng SQLite thông qua UserRepository.

Lần đầu chạy sẽ tự tạo DB và seed 2 tài khoản mặc định:
  operator / operator123   (role: operator)
  admin    / admin123      (role: admin)
"""
from __future__ import annotations

import logging
from typing import Optional

from banana_ai.auth.models import Role, User
from banana_ai.database.connection import init_database
from banana_ai.database.user_repository import UserRepository

logger = logging.getLogger(__name__)

_DB_PATH: str = "data/processed/banana_ai.db"
_repo: Optional[UserRepository] = None


def _get_repo() -> UserRepository:
    global _repo
    if _repo is None:
        _repo = UserRepository(_DB_PATH)
    return _repo


def init_auth(db_path: str) -> None:
    """Gọi 1 lần khi khởi động app, truyền db_path từ config."""
    global _DB_PATH, _repo
    _DB_PATH = db_path
    _repo = None
    init_database(db_path)
    _seed_default_users(db_path)


def _seed_default_users(db_path: str) -> None:
    """Tạo tài khoản mặc định nếu DB trống."""
    repo = UserRepository(db_path)
    defaults = [
        ("operator", "operator123", "Nhân viên mặc định", "NV-000", "operator"),
        ("admin",    "admin123",    "Quản trị viên",      "NV-001", "admin"),
    ]
    for username, password, full_name, employee_id, role in defaults:
        if repo.get_by_username(username) is None:
            try:
                repo.create(username, password, full_name, employee_id, role)
                logger.info("Seeded default user '%s'", username)
            except Exception as exc:
                logger.warning("Seed user '%s' failed: %s", username, exc)


def login(username: str, password: str) -> Optional[User]:
    """Xác thực và trả về User nếu hợp lệ, None nếu sai."""
    repo = _get_repo()
    try:
        db_user = repo.authenticate(username, password)
    except PermissionError as exc:
        logger.warning(str(exc))
        return None

    if db_user is None:
        logger.warning("Failed login for '%s'", username)
        return None

    # Map role string -> Role enum
    role_map = {"operator": Role.OPERATOR, "admin": Role.ADMIN, "manager": Role.MANAGER}
    role = role_map.get(db_user.role, Role.OPERATOR)

    logger.info("User '%s' logged in as %s", username, role.value)
    return User(
        username=db_user.username,
        role=role,
        db_id=db_user.id,
        full_name=db_user.full_name,
        employee_id=db_user.employee_id,
    )


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """Đổi mật khẩu. Trả về True nếu thành công."""
    repo = _get_repo()
    db_user = repo.authenticate(username, old_password)
    if db_user is None:
        return False
    repo.update_password(db_user.id, new_password)
    return True
