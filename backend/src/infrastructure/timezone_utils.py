"""
Timezone utilities for Brazilian time (UTC-3)
"""

from datetime import datetime, timezone, timedelta
import pytz

# Brazilian timezone (Brasília - UTC-3)
BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')


def now_brazil() -> datetime:
    """
    Get current datetime in Brazilian timezone (UTC-3)
    Returns timezone-aware datetime
    """
    return datetime.now(BRAZIL_TZ)


def utc_to_brazil(dt: datetime) -> datetime:
    """
    Convert UTC datetime to Brazilian timezone

    Args:
        dt: datetime object (can be naive or aware)

    Returns:
        timezone-aware datetime in Brazilian timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(BRAZIL_TZ)


def brazil_to_utc(dt: datetime) -> datetime:
    """
    Convert Brazilian timezone datetime to UTC

    Args:
        dt: datetime object in Brazilian timezone

    Returns:
        timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Localize to Brazilian timezone
        dt = BRAZIL_TZ.localize(dt)

    return dt.astimezone(timezone.utc)


def format_brazil_datetime(dt: datetime, format_str: str = "%d/%m/%Y %H:%M:%S") -> str:
    """
    Format datetime in Brazilian timezone

    Args:
        dt: datetime object
        format_str: strftime format string

    Returns:
        formatted string in Brazilian timezone
    """
    brazil_dt = utc_to_brazil(dt) if dt.tzinfo else BRAZIL_TZ.localize(dt)
    return brazil_dt.strftime(format_str)
