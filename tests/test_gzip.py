import os

from iokit import Gzip, Json, load_file, save_temp


def random_utf8_string(length: int) -> str:
    random_bytes = os.urandom(length)
    string = random_bytes.decode("utf-8", errors="replace")
    return string


def test_gzip_state() -> None:
    data = {"a": 1, "b": 2}
    state = Gzip(Json(data, name="data"))
    assert state.name == "data.json.gz"
    assert state.name.stem == "data"
    assert state.name.suffix == "gz"
    assert state.name.suffixes == ("json", "gz")
    assert state.load().load() == data
    assert state.size > 0


def test_gzip_compression() -> None:
    string = random_utf8_string(10_000)
    state = Json(string, name="data")
    loaded_string = state.load()
    compressed1 = Gzip(state)
    compressed3 = Gzip(state, compression=3)
    compressed9 = Gzip(state, compression=9)
    assert compressed1.size > compressed3.size
    assert compressed3.size > compressed9.size
    assert loaded_string == string
    assert compressed1.load().load() == string
    assert compressed3.load().load() == string
    assert compressed9.load().load() == string


def test_gzip_save_load_file() -> None:
    data = {"a": 1, "b": 2}
    state = Gzip(Json(data, name="data"))
    with save_temp(state) as path:
        assert load_file(path).load().load() == data
        assert path.as_posix().endswith(".json.gz")
        assert load_file(path).load().load() == data
