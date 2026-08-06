import gzip
import os

from iokit import FileState, Gzip, Json, Txt
from iokit.dtype.data import Data


def random_utf8_string(length: int) -> str:
    random_bytes = os.urandom(length)
    return random_bytes.decode("utf-8", errors="replace")


def test_gzip_state() -> None:
    data = {"a": 1, "b": 2}
    source = Json(data, path="data.json")
    state = Gzip(source)
    assert state.name == "data.json.gz"
    assert state.size > 0
    assert state.load().data == source.data
    assert state.load().load() == data


def test_gzip_keeps_key_and_timestamp() -> None:
    source = Txt("payload", path="nested/dir/данные.txt", timestamp=1_700_000_000)
    state = Gzip(source)
    assert state.path == "nested/dir/данные.txt.gz"
    assert state.timestamp == source.timestamp
    inner = state.load()
    assert inner.path == source.path
    assert inner.timestamp == source.timestamp
    assert inner.data == source.data


def test_gzip_compression() -> None:
    string = random_utf8_string(10_000)
    state = Json(string, path="data.json")
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


def test_gzip_is_a_plain_gzip_file() -> None:
    state = Gzip(Txt("payload", path="data.txt"))
    assert gzip.decompress(state.data) == b"payload"


def test_gzip_of_the_same_payload_is_the_same_bytes() -> None:
    source = Txt("payload", path="data.txt")
    assert Gzip(source).data == Gzip(source).data


def test_gzip_of_a_foreign_stream() -> None:
    state = Gzip(Data(gzip.compress(b"payload")), path="data.txt.gz")
    inner = state.load()
    assert inner.path == "data.txt"
    assert inner.data == b"payload"


def test_gzip_save_load_file() -> None:
    data = {"a": 1, "b": 2}
    state = Gzip(Json(data, path="data.json"))
    with state.save_temp() as temp_state:
        path = temp_state.path
        assert Gzip.from_state(FileState(path)).load().load() == data
        assert path.endswith(".json.gz")
