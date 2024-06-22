from datetime import datetime
from io import BytesIO

import pytz

Payload = BytesIO | bytes


def now() -> datetime:
    return datetime.now(pytz.utc)


class StateName:
    def __init__(self, name: str):
        self._name = name


class State:
    def __init__(self, data: Payload, name: str = "", mtime: datetime | None = None):
        self._data = BytesIO(data) if isinstance(data, bytes) else data
        self._name = StateName(name)
        self._mtime = mtime or now()
