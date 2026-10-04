"""A state held in memory hands out its bytes without copying them."""

import tracemalloc

from iokit import LoadedState

#: large enough for a copy to stand out
SIZE = 32 * 2**20


def test_loaded_state_shares_its_bytes() -> None:
    """Size, buffer and load allocate no copy."""
    state: LoadedState[bytes] = LoadedState(bytes(SIZE), path="data.bin")
    tracemalloc.start()
    try:
        assert state.size == SIZE
        with state.buffer as buffer:
            assert len(buffer.read()) == SIZE
        assert len(state.load()) == SIZE
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < SIZE // 2
