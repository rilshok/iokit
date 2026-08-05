from collections.abc import Iterable
from typing import Any

from iokit import Json, State, filter_states


def filter_states_(states: Iterable[State[Any]], pattern: str) -> list[State[Any]]:
    return list(filter_states(states, pattern))


def test_filter_states() -> None:
    banana = Json({"name": "banana"}, stem="banana")
    tomato = Json({"name": "tomato"}, stem="tomato")
    orange = Json({"name": "orange"}, stem="orange")
    cherry = Json({"name": "cherry"}, path="cherry.json")
    potato = Json({"name": "potato"}, stem="potato", path="potato.json")

    states = [banana, tomato, orange, cherry, potato]

    assert filter_states_(states, "") == []
    assert filter_states_(states, "*") == states
    assert filter_states_(states, "o*") == [orange]
    assert filter_states_(states, "o*") == [orange]
    assert filter_states_(states, "x*") == []
    assert filter_states_(states, "b*n") == [banana]
    assert filter_states_(states, "c*") == [cherry]
    assert filter_states_(states, "b*n*") == [banana]
    assert filter_states_(states, "p*t*") == [potato]
    assert filter_states_(states, "b*n*o") == []
    assert filter_states_(states, "[bpt]*") == [banana, tomato, potato]
    assert filter_states_(states, "[*") == []
    assert filter_states_(states, "t?mato*") == [tomato]
