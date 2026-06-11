"""User and role models."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Role(str, Enum):
    OPERATOR = "operator"
    MANAGER  = "manager"
    ADMIN    = "admin"   # alias cho manager, dùng trong DB


@dataclass
class User:
    username: str
    role: Role
    db_id: Optional[int] = field(default=None)   # id trong bảng users SQLite
    full_name: str = ""
    employee_id: str = ""

    @property
    def is_manager(self) -> bool:
        return self.role in (Role.MANAGER, Role.ADMIN)

    @property
    def can_export(self) -> bool:
        return self.is_manager

    @property
    def can_configure(self) -> bool:
        return self.is_manager

    @property
    def can_manage_users(self) -> bool:
        return self.role == Role.ADMIN
