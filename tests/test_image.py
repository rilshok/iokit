"""What an image is written as, over and above what every format owes in the contract."""

import numpy as np
import pytest
from PIL import Image as PillowImage

from iokit import Image, Jpeg, Jpg, LoadedState, Png

SIDE = 100


def picture() -> PillowImage.Image:
    """A picture of a plain red square, small enough for the sizes below to mean something."""
    return PillowImage.new("RGB", (SIDE, SIDE), color="red")


@pytest.mark.parametrize(
    ("kind", "smallest", "largest"),
    [(Jpeg, 800, 900), (Jpg, 800, 900), (Png, 200, 300)],
)
def test_encoding_of_each_format(
    kind: type[Image],
    smallest: int,
    largest: int,
) -> None:
    """Each format writes the same picture at the size its own encoding calls for."""
    state = kind(picture(), stem="picture")
    assert smallest < state.size < largest
    assert state.load().size == (SIDE, SIDE)


def test_jpg_and_jpeg_are_one_encoding() -> None:
    """`.jpg` and `.jpeg` differ in the name alone, the bytes under them being the same."""
    assert Jpg(picture(), stem="picture").data == Jpeg(picture(), stem="picture").data


def test_jpeg_read_under_either_spelling() -> None:
    state = Jpeg(picture(), path="picture.jpeg")
    same = LoadedState(bytes(state.data), path="picture.jpg")
    np.testing.assert_allclose(np.asarray(same.load()), np.asarray(state.load()), atol=0.1)
