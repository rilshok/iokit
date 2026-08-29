"""Timestamp utilities."""

from datetime import datetime, timedelta, timezone

from typing_extensions import Self


class Timestamp(float):
    """A float subclass representing seconds since epoch in UTC."""

    @classmethod
    def now(cls) -> Self:
        """Create a timestamp for the current moment in UTC.

        Returns:
            A timestamp of the current time.

        """
        return cls(datetime.now(timezone.utc).timestamp())

    @classmethod
    def from_datetime(cls, dt: datetime) -> Self:
        """Create a timestamp from a datetime object.

        Args:
            dt: A datetime object.

        Returns:
            A timestamp representing the same moment.

        """
        return cls(dt.timestamp())

    @property
    def datetime(self) -> datetime:
        """Get the UTC datetime this timestamp represents.

        Returns:
            A datetime object in UTC timezone.

        """
        return datetime.fromtimestamp(self, tz=timezone.utc)

    def shift(self, td: timedelta) -> Self:
        """Create a new timestamp by adding a time delta.

        Args:
            td: A timedelta to add to this timestamp.

        Returns:
            A new timestamp offset by the given delta.

        """
        return type(self).from_datetime(self.datetime + td)
