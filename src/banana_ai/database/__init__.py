"""
Database package — SQLite layer cho Banana AI.

Sử dụng:
    from banana_ai.database import init_database, UserRepository, SessionRepository, AnalyticsRepository
"""

from banana_ai.database.connection import init_database, get_connection
from banana_ai.database.models import User, ScanSession, ScanAnalytics
from banana_ai.database.user_repository import UserRepository
from banana_ai.database.session_repository import SessionRepository
from banana_ai.database.analytics_repository import AnalyticsRepository

__all__ = [
    "init_database",
    "get_connection",
    "User",
    "ScanSession",
    "ScanAnalytics",
    "UserRepository",
    "SessionRepository",
    "AnalyticsRepository",
]