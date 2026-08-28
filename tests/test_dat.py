from iokit import Dat


def test_dat() -> None:
    state = Dat(b"test", path="test.dat")
    assert state.name == "test.dat"
    assert state.load() == b"test"
