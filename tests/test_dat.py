from iokit import Dat, State


def test_dat() -> None:
    state = Dat(b"test", name="test")
    assert state.name == "test.dat"
    assert state.load() == b"test"


def load_dat() -> None:
    state = State(b"test", name="test.dat")
    assert state.load() == b"test"
    assert isinstance(state.cast(), Dat)
