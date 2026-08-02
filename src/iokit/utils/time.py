from datetime import UTC, datetime, timedelta
from typing import Self


def fromtimestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, UTC)


def now() -> datetime:
    return datetime.now(UTC)


class Timestamp(int):
    def __new__(cls, dt: int | None = None) -> Self:
        if dt is None:
            dt = int(now().timestamp())
        return super().__new__(cls, dt)

    @classmethod
    def from_dt(cls, dt: datetime) -> Self:
        return cls(int(dt.timestamp()))

    @property
    def dt(self) -> datetime:
        return datetime.fromtimestamp(self, tz=UTC)

    def shift(self, td: timedelta) -> int:
        return Timestamp.from_dt(self.dt + td)
