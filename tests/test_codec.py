"""How a codec is picked for a name: by the longest extension the name ends with.

The registry is shared by the whole process, so each test registers under an extension of its
own and leaves the others as they were.
"""

from uuid import uuid4

import pytest

from iokit.codec.base import best_codec, registrate
from iokit.codec.bin import BinCodec
from iokit.codec.json import JsonCodec
from iokit.codec.text import TextCodec

TEXT = "iokit.codec.text:TextCodec"
BIN = "iokit.codec.bin:BinCodec"
MISSING = "iokit-missing-package>=1"


def _extension() -> str:
    """An extension no codec has been registered for."""
    return f".x{uuid4().hex}"


def test_codec_by_extension() -> None:
    assert isinstance(best_codec("data.json"), JsonCodec)
    assert isinstance(best_codec("DATA.JSON"), JsonCodec)


def test_codec_ignores_case() -> None:
    ext = _extension()
    registrate(ext.upper(), TEXT)
    assert isinstance(best_codec(f"data{ext}"), TextCodec)
    assert isinstance(best_codec(f"data{ext.upper()}"), TextCodec)


def test_codec_of_a_path() -> None:
    """Only the end of the name counts, whatever dots the directories have."""
    assert isinstance(best_codec("archive.v1/data.json"), JsonCodec)
    assert isinstance(best_codec("archive.json/data"), BinCodec)


def test_codec_bare_extension() -> None:
    """A name no extension is registered for falls to the codec of the bare one."""
    assert isinstance(best_codec("data"), BinCodec)
    assert isinstance(best_codec(f"data{_extension()}"), BinCodec)


def test_codec_longest_extension() -> None:
    """The longest extension wins, whichever was registered first."""
    ext = _extension()
    registrate(f".outer{ext}", BIN)
    registrate(ext, TEXT)
    assert isinstance(best_codec(f"data{ext}"), TextCodec)
    assert isinstance(best_codec(f"data.outer{ext}"), BinCodec)
    assert isinstance(best_codec(f"data.other{ext}"), TextCodec)
    # an extension starts at a dot, not in the middle of a word
    assert isinstance(best_codec(f"data.router{ext}"), TextCodec)


def test_codec_registered_first() -> None:
    """Of codecs for one extension the first registered wins, unless another overrides it."""
    ext = _extension()
    registrate(ext, TEXT)
    registrate(ext, BIN)
    assert isinstance(best_codec(f"data{ext}"), TextCodec)
    registrate(ext, BIN, override=True)
    assert isinstance(best_codec(f"data{ext}"), BinCodec)


def test_codec_missing_dependency() -> None:
    """A codec lacking its dependencies gives way to the next one of its extension."""
    ext = _extension()
    registrate(ext, TEXT, requirements=MISSING)
    registrate(ext, BIN)
    assert isinstance(best_codec(f"data{ext}"), BinCodec)


def test_codec_missing_dependency_keeps_extension() -> None:
    """A codec lacking its dependencies gives way to no codec of a shorter extension."""
    ext = _extension()
    registrate(ext, BIN)
    registrate(f".outer{ext}", TEXT, requirements=MISSING)
    with pytest.raises(ModuleNotFoundError, match="iokit-missing-package"):
        best_codec(f"data.outer{ext}")


def test_codec_all_dependencies_missing() -> None:
    ext = _extension()
    registrate(ext, TEXT, requirements=MISSING)
    registrate(ext, BIN, requirements=MISSING)
    with pytest.raises(ModuleNotFoundError, match="all 2 candidates failed"):
        best_codec(f"data{ext}")
