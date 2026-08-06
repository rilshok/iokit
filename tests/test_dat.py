from iokit import Dat, State


def test_dat() -> None:
    state = Dat(b"test", path="test.dat")
    assert state.name == "test.dat"
    assert state.load() == b"test"


def load_dat() -> None:
    state = State(b"test", path="test.dat")
    assert state.load() == b"test"
