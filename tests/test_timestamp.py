"""Timestamp: seconds since epoch in UTC, carried as a float."""

from datetime import datetime, timedelta, timezone

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
