"""The waveform itself: what it is made of, and what can be done to it.

That a waveform survives each audio format is checked in `tests/test_state_contract.py`.
"""

import os
import subprocess
import sys

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


def test_waveform_is_measured() -> None:
    waveform = steady()
    assert waveform.frames == FREQ
    assert waveform.channels == 2
    assert waveform.duration == 1.0
    assert waveform.wave.dtype == np.float32


def test_one_dimensional_wave_is_mono() -> None:
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
def test_bad_wave_shape_refused(
    shape: tuple[int, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Waveform(wave=np.ones(shape, dtype=np.float32), freq=FREQ)


def test_to_mono_averages_channels() -> None:
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
def test_cut_keeps_named_frames(
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
def test_conversion_between_formats(
    name: str,
    kind: type[Audio],
    extension: str,
) -> None:
    """A waveform goes to a format by name, an audio state to another format by attribute."""
    written = getattr(steady(frames=2048), f"to_{name}")("sound")
    assert isinstance(written, kind)
    assert written.name == "sound" + extension

    rewritten = getattr(Wav(steady(frames=2048), path="nested/sound.wav"), name)
    assert isinstance(rewritten, kind)
    assert rewritten.path == "nested/sound" + extension
    assert rewritten.load().frames == 2048


#: a stack small enough to keep the check quick, and large enough for the interpreter itself
STACK_BYTES = 2 * 1024 * 1024

#: more frames than fit on that stack, libsndfile taking four bytes of it for each of them
LONG_FRAMES = 800_000

#: a conversion run apart, so that a stack the encoding overruns takes nothing else down
LONG_CONVERSION = """
import resource

_, hard = resource.getrlimit(resource.RLIMIT_STACK)
resource.setrlimit(resource.RLIMIT_STACK, ({stack}, hard))

import numpy as np

from iokit.dtype.waveform import Waveform

waveform = Waveform(wave=np.full(({frames}, 2), 0.5, dtype=np.float32), freq={freq})
print(waveform.to_{name}("sound").load().frames)
"""


@pytest.mark.skipif(os.name != "posix", reason="the stack is bounded through a posix resource")
@pytest.mark.parametrize("name", [name for name, _, _ in CONVERSIONS])
def test_long_wave_is_written_within_the_stack(name: str) -> None:
    """A wave longer than the stack holds goes to a format, and comes back whole.

    Handed a whole wave at once, libsndfile lays out four bytes of stack for every frame of
    it, so a long enough one overruns the stack and takes the process down with it. The wave
    has to reach it in blocks, which is what a run of `LONG_FRAMES` frames on a stack of
    `STACK_BYTES` bytes checks.
    """
    script = LONG_CONVERSION.format(
        stack=STACK_BYTES,
        frames=LONG_FRAMES,
        freq=FREQ,
        name=name,
    )
    conversion = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert conversion.returncode == 0, (
        f"converting to {name} left the process with {conversion.returncode}"
        f" (-11 being a stack overrun): {conversion.stderr}"
    )
    assert int(conversion.stdout) == LONG_FRAMES
