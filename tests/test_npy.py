import numpy as np

from iokit import Npy


def test_npy() -> None:
    array = np.random.rand(3, 2)
    state = Npy(array, name="test")
    assert str(state.name) == "test.npy"
    np.testing.assert_array_equal(state.load(), array)
