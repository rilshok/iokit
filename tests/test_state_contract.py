"""The contract every state of a known format keeps, checked on each implementation.

What each format does with a payload of its own is checked next to it, in `tests/test_document.py`
and its neighbours. What is here is what holds whatever the format is: the extension closes the
name, the size is the length of the data, and the payload comes back from the bytes however they
travelled - through a file, through a layer, or through nothing but their own extension.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from PIL import Image as PillowImage

from iokit import (
    Bin,
    Csv,
    Dat,
    Env,
    Flac,
    FormatState,
    Gzip,
    Jpeg,
    Jpg,
    Json,
    Jsonl,
    LoadedState,
    Mp3,
    Npy,
    Oga,
    Ogg,
    Opus,
    Png,
    State,
    Tsv,
    Txt,
    Wav,
    Waveform,
    Yaml,
    Yml,
    file,
)

#: a payload is whatever the format it is filed under carries, so nothing narrower fits
Payload = Any
#: what it means, for a given format, that a payload came back unharmed
Same = Callable[[Payload, Payload], None]


def alike(loaded: Payload, payload: Payload) -> None:
    """Assert a payload came back as it went in, which most formats mean literally."""
    assert loaded == payload


def alike_array(loaded: Payload, payload: Payload) -> None:
    """An array comes back with its values, its shape and the type of its entries."""
    assert loaded.dtype == payload.dtype
    np.testing.assert_array_equal(loaded, payload)


def alike_frame(loaded: Payload, payload: Payload) -> None:
    """A frame comes back with its columns, in the order and the types it had."""
    assert loaded.equals(payload)


def alike_image(loaded: Payload, payload: Payload) -> None:
    """An image comes back at its size and in its colours, which a lossy format only nears."""
    assert loaded.size == payload.size
    assert loaded.mode == payload.mode
    np.testing.assert_allclose(
        np.asarray(loaded, dtype=float).mean(axis=(0, 1)),
        np.asarray(payload, dtype=float).mean(axis=(0, 1)),
        atol=2.0,
    )


def alike_waveform(loaded: Payload, payload: Payload) -> None:
    """A waveform comes back at its rate and length, its loudness only neared by a lossy one."""
    assert loaded.freq == payload.freq
    assert loaded.channels == payload.channels
    assert loaded.frames == payload.frames
    rms = np.sqrt((loaded.wave.astype(float) ** 2).mean())
    np.testing.assert_allclose(rms, np.sqrt((payload.wave.astype(float) ** 2).mean()), atol=0.01)


def tone() -> Waveform:
    """An eighth of a second of a 1 kHz tone, which every audio format carries as it is."""
    time = np.arange(6_000) / 48_000
    wave = (0.5 * np.sin(2 * np.pi * 1000 * time)).astype(np.float32)
    return Waveform(wave=np.stack([wave, wave], axis=1), freq=48_000)


DOCUMENT: dict[str, Any] = {"list": [1, 2, 3], "str": "hello", "int": 42, "юникод": "значение"}
RECORDS: list[dict[str, Any]] = [{"a": number, "bb": number**2} for number in range(5)]
FRAME = pd.DataFrame([{"name": "Alice", "age": 24}, {"name": "Bob", "age": 25}])
IMAGE = PillowImage.new("RGB", (100, 100), color="red")


@dataclass(frozen=True)
class Kind:
    """A format, a payload to put through it, and what coming back unharmed means for it."""

    state: type[FormatState[Any]]
    payload: Payload
    same: Same = alike

    @property
    def name(self) -> str:
        return self.state.__name__.lower()


KINDS = [
    Kind(Dat, bytes(range(256))),
    Kind(Bin, b""),
    Kind(Txt, "Hello, World!\nこんにちは、世界!"),
    Kind(Json, DOCUMENT),
    Kind(Yaml, DOCUMENT),
    Kind(Yml, DOCUMENT),
    Kind(Jsonl, RECORDS),
    Kind(Env, {"login": "user", "password": "pass"}),
    Kind(Npy, np.arange(6, dtype=np.float64).reshape(3, 2), alike_array),
    Kind(Csv, FRAME, alike_frame),
    Kind(Tsv, FRAME, alike_frame),
    Kind(Png, IMAGE, alike_image),
    Kind(Jpeg, IMAGE, alike_image),
    Kind(Jpg, IMAGE, alike_image),
    Kind(Wav, tone(), alike_waveform),
    Kind(Flac, tone(), alike_waveform),
    Kind(Mp3, tone(), alike_waveform),
    Kind(Ogg, tone(), alike_waveform),
    Kind(Oga, tone(), alike_waveform),
    Kind(Opus, tone(), alike_waveform),
]


@pytest.fixture(params=KINDS, ids=[kind.name for kind in KINDS], name="kind")
def kind_fixture(request: pytest.FixtureRequest) -> Kind:
    """Every format a payload can be filed under, and the payload to file."""
    kind: Kind = request.param
    return kind


@pytest.fixture(name="state")
def state_fixture(kind: Kind) -> FormatState[Any]:
    """The payload of the kind, encoded under the stem `greeting`."""
    return kind.state(kind.payload, "greeting")


def test_the_stem_is_closed_by_the_extension_of_the_format(
    kind: Kind,
    state: FormatState[Any],
) -> None:
    extension = kind.state.extension()
    assert state.path == "greeting" + extension
    assert state.name == "greeting" + extension
    assert state.stem == "greeting"
    assert state.suffix == extension


def test_the_size_is_the_length_of_the_data(state: FormatState[Any]) -> None:
    assert state.size == len(state.data)


def test_a_payload_comes_back_from_the_state_it_was_encoded_into(
    kind: Kind,
    state: FormatState[Any],
) -> None:
    kind.same(state.load(), kind.payload)


def test_a_payload_comes_back_from_bytes_named_by_the_extension_alone(
    kind: Kind,
    state: FormatState[Any],
) -> None:
    """Nothing but the extension of the name says how to read a record back."""
    plain: State[Any] = LoadedState(bytes(state.data), path=state.name)
    kind.same(plain.load(), kind.payload)


def test_a_state_is_rebuilt_from_another_holding_its_bytes(
    kind: Kind,
    state: FormatState[Any],
) -> None:
    plain: State[Any] = LoadedState(bytes(state.data), path=state.name, timestamp=1_700_000_000)
    rebuilt = kind.state.from_state(plain)
    # the state is taken over whole: where it goes, when it was touched, and what it holds
    assert rebuilt.path == plain.path
    assert rebuilt.timestamp == plain.timestamp
    kind.same(rebuilt.load(), kind.payload)


def test_a_payload_survives_the_trip_through_a_file(
    kind: Kind,
    state: FormatState[Any],
    tmp_path: Path,
) -> None:
    saved = state.save(tmp_path)
    assert Path(saved.path).read_bytes() == state.data
    kind.same(file(saved.path).load(), kind.payload)


def test_a_payload_survives_a_layer_laid_over_the_state(
    kind: Kind,
    state: FormatState[Any],
) -> None:
    """A state keeps its path and its payload under a layer.

    One layer says it for all of them: what a layer carries is bytes, and which bytes they are
    is nothing it knows. The layers themselves are checked in `tests/test_layer.py`.
    """
    packed = Gzip(state, compression=9)
    assert packed.path == state.path + ".gz"
    kind.same(packed.load().load(), kind.payload)
