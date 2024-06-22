from typing import Iterable

from iokit import Json, State, filter_states


def filter_states_(states: Iterable[State], pattern: str) -> list[State]:
    return list(filter_states(states, pattern))


def test_filter_states() -> None:
    banana = Json({"name": "banana"}, name="banana")
    tomato = Json({"name": "tomato"}, name="tomato")
    orange = Json({"name": "orange"}, name="orange")
    cherry = Json({"name": "cherry"}, name="cherry")
    potato = Json({"name": "potato"}, name="potato")

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
