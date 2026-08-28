"""SAT-SA Backend API Gateway Microservice Package."""

import os

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_backend_app_dir = os.path.join(_backend_dir, "app")

__path__ = [_backend_app_dir, _backend_dir]

from backend.config import backend_settings
from backend.main import app

__all__ = ["app", "backend_settings"]
