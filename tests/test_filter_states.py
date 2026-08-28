from collections.abc import Iterable
from typing import Any

from iokit import Json, State, filtrate


def filtrate_states_(states: Iterable[State[Any]], pattern: str) -> list[State[Any]]:
    return list(filtrate(states, pattern))


def test_filtrate_states() -> None:
    banana = Json({"name": "banana"}, stem="banana")
    tomato = Json({"name": "tomato"}, stem="tomato")
    orange = Json({"name": "orange"}, stem="orange")
    cherry = Json({"name": "cherry"}, path="cherry.json")
    potato = Json({"name": "potato"}, stem="potato", path="potato.json")

    states = [banana, tomato, orange, cherry, potato]

    assert filtrate_states_(states, "") == []
    assert filtrate_states_(states, "*") == states
    assert filtrate_states_(states, "o*") == [orange]
    assert filtrate_states_(states, "x*") == []
    assert filtrate_states_(states, "b*n") == [banana]
    assert filtrate_states_(states, "c*") == [cherry]
    assert filtrate_states_(states, "b*n*") == [banana]
    assert filtrate_states_(states, "p*t*") == [potato]
    assert filtrate_states_(states, "b*n*o") == []
    assert filtrate_states_(states, "[bpt]*") == [banana, tomato, potato]
    assert filtrate_states_(states, "[*") == []
    assert filtrate_states_(states, "t?mato*") == [tomato]
