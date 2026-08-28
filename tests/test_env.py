"""What a dotenv file spells out, over and above what every format owes in the contract."""

import pytest

from iokit import Env


def test_a_variable_declared_without_a_value_is_written_bare_and_loads_as_none() -> None:
    state = Env({"login": "user", "empty": None}, stem="creds")
    assert state.data == b"login='user'\nempty\n"
    assert state.load() == {"login": "user", "empty": None}


@pytest.mark.parametrize("value", ["a b", "a'b", "a\\b", "a\nb", ""])
def test_a_value_dotenv_would_read_as_something_else_is_written_so_it_does_not(value: str) -> None:
    """Quoting and escaping are the codec's to get right, whatever the value carries."""
    assert Env({"key": value}, stem="creds").load() == {"key": value}
