import numpy as np
from PIL import Image

from iokit import Jpeg, Png, State


def test_jpeg() -> None:
    image = Image.new("RGB", (100, 100), color="red")
    state = Jpeg(image, name="test")
    assert str(state.name) == "test.jpeg"
    assert 800 < state.size < 900
    assert state.load().size == (100, 100)
    raw = State(state.data, name="test.jpg").cast()
    assert isinstance(raw, Jpeg)
    np.testing.assert_allclose(raw.load(), state.load(), atol=0.1)


def test_png() -> None:
    image = Image.new("RGB", (100, 100), color="red")
    state = Png(image, name="test")
    assert str(state.name) == "test.png"
    assert 200 < state.size < 300
    assert state.load().size == (100, 100)
