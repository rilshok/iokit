"""A state held in memory hands out its bytes without copying them."""

import tracemalloc
from collections.abc import Callable
from pathlib import Path

from iokit import Bin, LoadedState, file

#: large enough for a copy to stand out
SIZE = 32 * 2**20


def _peak(action: Callable[[], object]) -> int:
    """Return the memory peak of `action`, in bytes."""
    tracemalloc.start()
    try:
        action()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_loaded_state_shares_its_bytes() -> None:
    """Size, buffer and load allocate no copy."""
    state: LoadedState[bytes] = LoadedState(bytes(SIZE), path="data.bin")

    def read() -> None:
        assert state.size == SIZE
        with state.buffer as buffer:
            assert len(buffer.read()) == SIZE
        assert len(state.load()) == SIZE

    assert _peak(read) < SIZE // 2


def test_format_shares_loaded_bytes() -> None:
    """A format made of a loaded state takes its bytes without a copy."""
    source: LoadedState[bytes] = LoadedState(bytes(SIZE), path="data.bin")
    assert _peak(lambda: Bin.from_state(source).load()) < SIZE // 2


def test_format_reads_a_file_once(tmp_path: Path) -> None:
    """A format made of a file reads it into a single copy."""
    path = Bin(bytes(SIZE), "data").save(tmp_path).path
    assert _peak(lambda: Bin.from_state(file(path)).load()) < SIZE * 3 // 2
