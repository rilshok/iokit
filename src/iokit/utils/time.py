from datetime import UTC, datetime, timedelta
from typing import Self


class Timestamp(float):
    @classmethod
    def now(cls) -> Self:
        return cls(datetime.now(UTC).timestamp())

    @classmethod
    def from_datetime(cls, dt: datetime) -> Self:
        return cls(dt.timestamp())

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self, tz=UTC)

    def shift(self, td: timedelta) -> Self:
        return type(self).from_datetime(self.datetime + td)
