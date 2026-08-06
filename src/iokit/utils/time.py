from datetime import datetime, timedelta, timezone

from typing_extensions import Self


class Timestamp(float):
    @classmethod
    def now(cls) -> Self:
        return cls(datetime.now(timezone.utc).timestamp())

    @classmethod
    def from_datetime(cls, dt: datetime) -> Self:
        return cls(dt.timestamp())

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self, tz=timezone.utc)

    def shift(self, td: timedelta) -> Self:
        return type(self).from_datetime(self.datetime + td)
