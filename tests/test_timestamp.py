"""Timestamp: seconds since epoch in UTC, carried as a float."""

from datetime import datetime, timedelta, timezone

import pytest

from iokit import Timestamp

MOMENT = datetime(2017, 1, 1, tzinfo=timezone.utc)


def test_timestamp_is_a_float() -> None:
    assert Timestamp(1.5) == 1.5  # noqa: PLR2004
    assert isinstance(Timestamp(0), float)


def test_timestamp_now_is_the_current_moment() -> None:
    before = datetime.now(timezone.utc).timestamp()
    now = Timestamp.now()
    after = datetime.now(timezone.utc).timestamp()
    assert before <= now <= after


def test_timestamp_survives_a_datetime_round_trip() -> None:
    timestamp = Timestamp.from_datetime(MOMENT)
    assert timestamp == MOMENT.timestamp()
    assert timestamp.datetime == MOMENT
    assert timestamp.datetime.tzinfo == timezone.utc


def test_timestamp_shift_moves_by_the_delta() -> None:
    shifted = Timestamp.from_datetime(MOMENT).shift(timedelta(hours=1))
    assert isinstance(shifted, Timestamp)
    assert shifted.datetime == MOMENT + timedelta(hours=1)


@pytest.mark.parametrize(
    "value",
    [
        "2017-01-01T00:00:00Z",
        "2017-01-01T03:00:00+03:00",
        "Sun, 01 Jan 2017 00:00:00 GMT",
        "2017-01-01 00:00:00",
    ],
)
def test_timestamp_from_str(value: str) -> None:
    timestamp = Timestamp.from_str(value)
    assert isinstance(timestamp, Timestamp)
    assert timestamp.datetime == MOMENT


def test_timestamp_from_str_refuses_garbage() -> None:
    with pytest.raises(ValueError, match="Unknown string format"):
        Timestamp.from_str("not a date")
