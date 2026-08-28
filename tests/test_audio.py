"""The waveform itself: what it is made of, and what can be done to it.

That a waveform survives each audio format is checked in `tests/test_state_contract.py`.
"""

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from iokit import Audio, Flac, Mp3, Oga, Ogg, Opus, Wav
from iokit.dtype.waveform import Waveform

#: a rate every audio format takes, opus being picky about which ones it does
FREQ = 24_000


def steady(frames: int = FREQ, channels: int = 2) -> Waveform:
    """A wave of a steady half amplitude, one second of it by default."""
    return Waveform(wave=np.full((frames, channels), 0.5, dtype=np.float32), freq=FREQ)


def test_a_waveform_is_measured_in_frames_channels_and_seconds() -> None:
    waveform = steady()
    assert waveform.frames == FREQ
    assert waveform.channels == 2
    assert waveform.duration == 1.0
    assert waveform.wave.dtype == np.float32


def test_a_wave_of_one_dimension_is_taken_as_a_single_channel() -> None:
    waveform = Waveform(wave=np.ones(FREQ), freq=FREQ)
    assert waveform.channels == 1
    assert waveform.wave.shape == (FREQ, 1)


@pytest.mark.parametrize(
    ("shape", "message"),
    [
        ((FREQ, 2, 2), "but got 3D"),
        ((2, FREQ), "channels"),
    ],
)
def test_a_wave_of_a_shape_no_waveform_has_is_refused(
    shape: tuple[int, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Waveform(wave=np.ones(shape, dtype=np.float32), freq=FREQ)


def test_the_channels_are_averaged_into_one() -> None:
    waveform = Waveform(wave=np.stack([np.zeros(FREQ), np.ones(FREQ)], axis=1), freq=FREQ)
    mono = waveform.to_mono()
    assert mono.channels == 1
    assert_array_equal(mono.wave, np.full((FREQ, 1), 0.5, dtype=np.float32))
    # the waveform is left as it was, so taking it down to mono again gives the same wave
    assert_array_equal(waveform.to_mono().wave, mono.wave)
    assert_array_equal(mono.to_mono().wave, mono.wave)


@pytest.mark.parametrize(
    ("begin", "end", "kept"),
    [
        (0.5, 1.0, slice(FREQ // 2, None)),
        (0.5, None, slice(FREQ // 2, None)),
        (None, 0.5, slice(None, FREQ // 2)),
        (None, None, slice(None)),
        # an end past the wave is the end of the wave
        (0.5, 1.5, slice(FREQ // 2, None)),
    ],
)
def test_a_cut_keeps_the_frames_it_names(
    begin: float | None,
    end: float | None,
    kept: slice,
) -> None:
    waveform = steady()
    cut = waveform.cut(begin=begin, end=end)
    assert_array_equal(cut.wave, waveform.wave[kept])
    assert cut.duration == cut.frames / FREQ


CONVERSIONS = [
    ("wav", Wav, ".wav"),
    ("flac", Flac, ".flac"),
    ("mp3", Mp3, ".mp3"),
    ("ogg", Ogg, ".ogg"),
    ("oga", Oga, ".oga"),
    ("opus", Opus, ".opus"),
]


@pytest.mark.parametrize(("name", "kind", "extension"), CONVERSIONS)
def test_a_waveform_is_written_as_the_format_it_is_asked_for(
    name: str,
    kind: type[Audio],
    extension: str,
) -> None:
    """A waveform goes to a format by name, and an audio state to another format by attribute.

    Either way the stem stays where it is, and only the extension says what the bytes now are.
    """
    written = getattr(steady(frames=2048), f"to_{name}")("sound")
    assert isinstance(written, kind)
    assert written.name == "sound" + extension

    rewritten = getattr(Wav(steady(frames=2048), path="nested/sound.wav"), name)
    assert isinstance(rewritten, kind)
    assert rewritten.path == "nested/sound" + extension
    assert rewritten.load().frames == 2048
