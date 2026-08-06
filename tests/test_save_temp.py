from pathlib import Path

from iokit import FileState, Jsonl  # , load_file, save_temp


def test_save_temp_jsonl() -> None:
    data = [{"a": i, "b": i**2} for i in range(10)]
    state = Jsonl(data, path="data/test.jsonl")
    with state.save_temp() as temp_state:
        path = temp_state.path
        assert Path(path).name == "test.jsonl"
        state_loaded = FileState(path)
        assert state.size == state_loaded.size
        assert Path(path).stat().st_size == state.size
        assert state_loaded.name == "test.jsonl"
        loaded = state_loaded.load()
        assert len(loaded) == len(data)
        assert loaded == data
    assert not Path(path).exists()
