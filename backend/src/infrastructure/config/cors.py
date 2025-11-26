"""
CORS Configuration Module
Handles Cross-Origin Resource Sharing configuration
Following the Single Responsibility Principle (SRP) from SOLID
"""

import json
import os
from typing import List, Union, Optional


def parse_cors_origins(raw_value: Optional[str]) -> List[str]:
    """Parse CORS origins from env supporting JSON or comma-separated values."""
    if not raw_value:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    try:
        parsed = json.loads(raw_value)
        if isinstance(parsed, list):
            return [str(origin).strip() for origin in parsed if origin]
    except json.JSONDecodeError:
        pass

    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def get_cors_origins() -> List[str]:
    """Get CORS origins from environment variable"""
    return parse_cors_origins(os.getenv("CORS_ORIGINS"))