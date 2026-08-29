"""What a dotenv file spells out, over and above what every format owes in the contract."""

import pytest

from iokit import Env


def test_variable_without_a_value() -> None:
    state = Env({"login": "user", "empty": None}, stem="creds")
    assert state.data == b"login='user'\nempty\n"
    assert state.load() == {"login": "user", "empty": None}


@pytest.mark.parametrize("value", ["a b", "a'b", "a\\b", "a\nb", ""])
def test_awkward_values_round_trip(value: str) -> None:
    """Quoting and escaping are the codec's to get right, whatever the value carries."""
    assert Env({"key": value}, stem="creds").load() == {"key": value}
