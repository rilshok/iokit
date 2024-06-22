from datetime import datetime

from pytz import utc


def fromtimestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, utc)


def now() -> datetime:
    return datetime.now(utc)
