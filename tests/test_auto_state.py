import numpy as np
import pytest
from pandas import DataFrame

from iokit import (
    Csv,
    Dat,
    Enc,
    Flac,
    Gzip,
    Json,
    Mp3,
    Npy,
    Ogg,
    Tsv,
    Txt,
    Wav,
    Waveform,
    Yaml,
    auto_state,
)
from iokit.extensions.audio import AudioState


def test_auto_state_csv():
    frame = DataFrame([{"a": 1, "b": 4}, {"a": 2, "b": 5}, {"a": 3, "b": 6}])
    state = auto_state(frame, name="test")
    assert isinstance(state, Csv)
    assert str(state.name) == "test.csv"
    assert all(state.load()["a"] == [1, 2, 3])
    assert all(state.load()["b"] == [4, 5, 6])


def test_auto_state_dat():
    data = b"Hello, World!"
    state = auto_state(data, name="test")
    assert isinstance(state, Dat)
    assert str(state.name) == "test.dat"
    assert state.load() == data


def test_auto_state_enc():
    data = b"Hello, World!"
    state = auto_state(data, name="test", password="p@ssw0rd")
    assert isinstance(state, Enc)
    assert str(state.name) == "test.enc"
    enc = state.load()
    with pytest.raises(ValueError) as excinfo:
        enc.load("password")
        assert "Decryption failed" in str(excinfo.value)
    dec = enc.load("p@ssw0rd")
    assert isinstance(dec, Dat)
    assert str(dec.name) == "test.dat"
    assert dec.load() == data


def test_auto_state_gzip():
    data = b"Hello, World!"
    state = auto_state(data, name="test", compression=3)
    assert isinstance(state, Gzip)
    assert str(state.name) == "test.dat.gz"
    inner = state.load()
    assert isinstance(inner, Dat)
    assert str(inner.name) == "test.dat"
    assert inner.load() == data


def test_auto_state_json():
    data = {"a": 1, "b": 2}
    state = auto_state(data, name="test")
    assert isinstance(state, Json)
    assert str(state.name) == "test.json"
    assert state.load() == data


def test_auto_state_npy():
    data = np.array([1, 2, 3])
    state = auto_state(data, name="test")
    assert isinstance(state, Npy)
    assert str(state.name) == "test.npy"
    assert np.array_equal(state.load(), data)


def test_auto_state_tsv():
    frame = DataFrame([{"a": 1, "b": 4}, {"a": 2, "b": 5}, {"a": 3, "b": 6}])
    state = auto_state(frame, name="test", dataframe_to="tsv")
    assert isinstance(state, Tsv)
    assert str(state.name) == "test.tsv"
    assert all(state.load()["a"] == [1, 2, 3])
    assert all(state.load()["b"] == [4, 5, 6])


def test_auto_state_txt():
    data = "Hello, World!"
    state = auto_state(data, name="test")
    assert isinstance(state, Txt)
    assert str(state.name) == "test.txt"
    assert state.load() == data


@pytest.mark.parametrize(
    "waveform_to, klass",
    [
        ("wav", Wav),
        ("mp3", Mp3),
        ("ogg", Ogg),
        ("flac", Flac),
    ],
)
def test_auto_state_waveform_wav(waveform_to: str, klass: type[AudioState]):
    wave = np.zeros((44100, 2)) + 0.2
    assert wave.dtype == np.float64
    data = Waveform(wave=wave, freq=22050)
    state = auto_state(data, name="test", waveform_to=waveform_to)
    assert isinstance(state, klass)
    assert str(state.name) == f"test.{waveform_to}"
    loaded = state.load()
    assert isinstance(loaded, Waveform)

    np.testing.assert_allclose(loaded.wave, wave, atol=0.1)
    assert loaded.freq == data.freq == 22050
    assert loaded.wave.dtype == np.float32
    assert loaded.wave.shape == wave.shape == (44100, 2)


def test_auto_state_enc_compression():
    data = b"Hello, World!"
    state = auto_state(data, name="test", password="p@ssw0rd", compression=3)
    assert isinstance(state, Enc)
    assert str(state.name) == "test.enc"
    enc = state.load()
    with pytest.raises(ValueError) as excinfo:
        enc.load("password")
        assert "Decryption failed" in str(excinfo.value)
    dec = enc.load("p@ssw0rd")
    assert isinstance(dec, Gzip)
    assert str(dec.name) == "test.dat.gz"
    inner = dec.load()
    assert isinstance(inner, Dat)
    assert str(inner.name) == "test.dat"
    assert inner.load() == data


def test_auto_state_yaml():
    data = {"a": 1, "b": 2}
    state = auto_state(data, name="test", builtin_to="yaml")
    assert isinstance(state, Yaml)
    assert str(state.name) == "test.yaml"
    assert state.load() == data
