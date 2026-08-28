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
def test_the_pattern_says_which_states_are_kept(
    pattern: str,
    matched: list[State[Any]],
) -> None:
    assert list(filtrate(STATES, pattern)) == matched


def test_the_first_match_is_the_one_handed_back() -> None:
    assert first(STATES, "*") is BANANA
    assert first(STATES, "[po]*") is ORANGE


def test_asking_for_a_first_match_there_is_none_of_is_refused() -> None:
    with pytest.raises(FileNotFoundError, match="State not found"):
        first(STATES, "x*")
