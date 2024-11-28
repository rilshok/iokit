import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from iokit import Waveform


def test_audio_state() -> None:
    wavef_half = np.ones((22050, 2)) / 2
    wave = wavef_half + 0.01 * (np.random.RandomState(42).randn(22050, 2) - 0.5)
    waveform = Waveform(wave=wave, freq=22050)

    assert waveform.duration == 1.0
    assert waveform.channels == 2

    assert_allclose(waveform.to_flac("flac").load().wave, wavef_half, atol=0.1)
    assert_allclose(waveform.to_wav("wav").load().wave, wavef_half, atol=0.1)
    assert_allclose(waveform.to_mp3("mp3").load().wave, wavef_half, atol=0.3)
    assert_allclose(waveform.to_ogg("ogg").load().wave, wave, atol=0.3)

    waveform_mono = waveform.to_mono()
    assert_allclose(waveform_mono.wave[:, 0], wavef_half[:, 0], atol=0.1)
    waveform_mono_2 = waveform.to_mono()
    assert_array_equal(waveform_mono.wave, waveform_mono_2.wave)

    assert waveform_mono.channels == 1


def test_waveform_incorrect() -> None:
    with pytest.raises(ValueError) as excinfo:
        Waveform(wave=np.ones((22050, 2, 2)).astype(np.float32), freq=22050)
        assert "but got 3D" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        Waveform(wave=np.ones((2, 22050)).astype(np.float32), freq=22050)
        assert "more frames than channels" in str(excinfo.value)


def test_waveform_cut() -> None:
    waveform = Waveform(wave=np.ones((22050, 2)).astype(np.float32), freq=22050)
    waveform_cut = waveform.cut(begin=0.5, end=1.0)
    assert waveform_cut.duration == 0.5
    assert waveform_cut.wave.shape == (11025, 2)
    assert_array_equal(waveform_cut.wave, waveform.wave[11025:])

    waveform_cut = waveform.cut(begin=0.5)
    assert_array_equal(waveform_cut.wave, waveform.wave[11025:])

    waveform_cut = waveform.cut(end=0.5)
    assert_array_equal(waveform_cut.wave, waveform.wave[:11025])

    waveform_cut = waveform.cut()
    assert_array_equal(waveform_cut.wave, waveform.wave)

    waveform_cut = waveform.cut(begin=0.5, end=1.5)
    assert waveform_cut.duration == 0.5
    assert waveform_cut.wave.shape == (11025, 2)
    assert_array_equal(waveform_cut.wave, waveform.wave[11025:])
