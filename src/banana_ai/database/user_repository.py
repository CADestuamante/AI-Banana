"""
UserRepository — CRUD cho bảng users.
"""

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from banana_ai.database.connection import get_connection
from banana_ai.database.models import User


def _hash_password(password: str) -> str:
    """Hash mật khẩu bằng PBKDF2-HMAC-SHA256 với salt ngẫu nhiên."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + ":" + key.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    """Kiểm tra mật khẩu khớp với hash đã lưu."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
        return hmac.compare_digest(key, new_key)
    except Exception:
        return False


class UserRepository:
    """Thao tác CRUD với bảng users."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    # --- Tạo tài khoản ---

    def create(
        self,
        username: str,
        password: str,
        full_name: str,
        employee_id: str,
        role: str,
    ) -> User:
        if role not in ("admin", "operator"):
            raise ValueError(f"Role không hợp lệ: '{role}'.")
        password_hash = _hash_password(password)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        sql = """
            INSERT INTO users (username, password_hash, full_name, employee_id, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            with get_connection(self._db_path) as conn:
                cursor = conn.execute(sql, (username, password_hash, full_name, employee_id, role, now))
                conn.commit()
                return User(
                    id=cursor.lastrowid,
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    employee_id=employee_id,
                    role=role,
                    status="active",
                    created_at=datetime.fromisoformat(now),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Username hoặc mã nhân viên đã tồn tại. Chi tiết: {exc}") from exc

    # --- Đăng nhập ---

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_by_username(username)
        if user is None:
            return None
        if user.status == "blocked":
            raise PermissionError(f"Tài khoản '{username}' đã bị khóa.")
        if not _verify_password(password, user.password_hash):
            return None
        return user

    # --- Truy vấn ---

    def get_by_id(self, user_id: int) -> Optional[User]:
        with get_connection(self._db_path) as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row) if row else None

    def get_by_username(self, username: str) -> Optional[User]:
        with get_connection(self._db_path) as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return _row_to_user(row) if row else None

    def list_all(self) -> List[User]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [_row_to_user(r) for r in rows]

    def list_by_role(self, role: str) -> List[User]:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE role = ? ORDER BY full_name", (role,)
            ).fetchall()
        return [_row_to_user(r) for r in rows]

    # --- Cập nhật ---

    def update_status(self, user_id: int, status: str) -> None:
        if status not in ("active", "blocked"):
            raise ValueError(f"Status không hợp lệ: '{status}'.")
        with get_connection(self._db_path) as conn:
            conn.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
            conn.commit()

    def update_password(self, user_id: int, new_password: str) -> None:
        new_hash = _hash_password(new_password)
        with get_connection(self._db_path) as conn:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            conn.commit()

    def update_role(self, user_id: int, role: str) -> None:
        if role not in ("admin", "operator"):
            raise ValueError(f"Role không hợp lệ: '{role}'.")
        with get_connection(self._db_path) as conn:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            conn.commit()

    # --- Xóa ---

    def delete(self, user_id: int) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        full_name=row["full_name"],
        employee_id=row["employee_id"],
        role=row["role"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
    )