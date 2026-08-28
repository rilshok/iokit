"""Picking states out of a sequence by a glob over their names."""

from typing import Any

import pytest

from iokit import Json, State, filtrate, first

BANANA = Json({"name": "banana"}, stem="banana")
TOMATO = Json({"name": "tomato"}, stem="tomato")
ORANGE = Json({"name": "orange"}, stem="orange")
CHERRY = Json({"name": "cherry"}, path="cherry.json")
POTATO = Json({"name": "potato"}, stem="potato", path="potato.json")

STATES: list[State[Any]] = [BANANA, TOMATO, ORANGE, CHERRY, POTATO]


@pytest.mark.parametrize(
    ("pattern", "matched"),
    [
        ("", []),
        ("*", STATES),
        ("o*", [ORANGE]),
        ("x*", []),
        ("b*n", [BANANA]),
        ("c*", [CHERRY]),
        ("b*n*", [BANANA]),
        ("p*t*", [POTATO]),
        ("b*n*o", []),
        ("[bpt]*", [BANANA, TOMATO, POTATO]),
        ("[*", []),
        ("t?mato*", [TOMATO]),
    ],
)
def test_pattern_keeps_matching_states(
    pattern: str,
    matched: list[State[Any]],
) -> None:
    assert list(filtrate(STATES, pattern)) == matched


def test_first_match() -> None:
    assert first(STATES, "*") is BANANA
    assert first(STATES, "[po]*") is ORANGE


def test_no_match_refused() -> None:
    with pytest.raises(FileNotFoundError, match="State not found"):
        first(STATES, "x*")
