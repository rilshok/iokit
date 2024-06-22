from pathlib import Path

from iokit import Jsonl, load_file, save_temp


def test_save_temp_jsonl() -> None:
    data = [{"a": i, "b": i**2} for i in range(10)]
    state = Jsonl(data, name="test")
    with save_temp(state) as path:
        assert Path(path).name == "test.jsonl"
        state_loaded = load_file(path)
        assert state.size == state_loaded.size
        assert Path(path).stat().st_size == state.size
        assert state_loaded.name.stem == "test"
        loaded = state_loaded.load()
        assert len(loaded) == len(data)
        assert loaded == data
    assert not Path(path).exists()
