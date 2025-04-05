import numpy as np

from iokit import Npy


def test_npy() -> None:
    array = np.random.RandomState(1337).rand(3, 2)
    state = Npy(array, name="test")
    assert str(state.name) == "test.npy"
    assert state.size > 0
    np.testing.assert_array_equal(state.load(), array)
