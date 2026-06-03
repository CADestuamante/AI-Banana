"""User and role models."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    OPERATOR = "operator"
    MANAGER = "manager"


@dataclass
class User:
    username: str
    role: Role

    @property
    def is_manager(self) -> bool:
        return self.role == Role.MANAGER

    @property
    def can_export(self) -> bool:
        return self.role == Role.MANAGER

    @property
    def can_configure(self) -> bool:
        return self.role == Role.MANAGER