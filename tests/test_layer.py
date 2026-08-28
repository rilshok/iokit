"""What a layer does to the state it covers, checked on each layer there is.

That a payload of any format survives one is in `tests/test_state_contract.py`.
"""

import gzip
from dataclasses import dataclass, field
from typing import Any

import pytest

from iokit import (
    Data,
    Enc,
    Gzip,
    Json,
    LayerState,
    LoadedState,
    MemoryStorage,
    State,
    StateStorage,
    Txt,
)

PASSWORD = "pA$sw0Rd"  # noqa: S105
SALT = "s@lt"
SOURCE = Txt("payload", path="nested/dir/данные.txt", timestamp=1_700_000_000)


@dataclass(frozen=True)
class Layer:
    """A layer, and what it takes to lay it over a state and to take it off again."""

    kind: type[LayerState]
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.kind.__name__.lower()

    def over(self, state: State[Any]) -> LayerState:
        return self.kind(state, **self.config)


LAYERS = [Layer(Gzip), Layer(Enc, {"password": PASSWORD, "salt": SALT})]


@pytest.fixture(
    params=LAYERS,
    ids=[layer.name for layer in LAYERS],
    name="layer",
    scope="module",
)
def layer_fixture(request: pytest.FixtureRequest) -> Layer:
    """Every layer a state can be covered with, and the settings it is covered with."""
    layer: Layer = request.param
    return layer


@pytest.fixture(name="covered", scope="module")
def covered_fixture(layer: Layer) -> LayerState:
    """`SOURCE` under the layer, laid over once: deriving a key for it is not cheap."""
    return layer.over(SOURCE)


def test_a_layer_appends_its_extension_and_keeps_the_timestamp(
    layer: Layer,
    covered: LayerState,
) -> None:
    assert covered.path == SOURCE.path + layer.kind.extension()
    assert covered.timestamp == SOURCE.timestamp


def test_the_state_under_a_layer_comes_back_whole(layer: Layer, covered: LayerState) -> None:
    inner = covered.load(**layer.config)
    assert inner.path == SOURCE.path
    assert inner.timestamp == SOURCE.timestamp
    assert inner.data == SOURCE.data
    assert inner.load() == SOURCE.load()


def test_a_layer_is_taken_off_bytes_that_come_from_elsewhere(
    layer: Layer,
    covered: LayerState,
) -> None:
    """What a layer needs to come off is the bytes and the path, not the state that made them."""
    elsewhere: LoadedState[Any] = LoadedState(bytes(covered.data), path=covered.path)
    assert layer.kind.from_state(elsewhere).load(**layer.config).data == SOURCE.data


def test_a_layer_hides_the_payload_it_covers(covered: LayerState) -> None:
    assert b"payload" not in bytes(covered.data)


# compressing


def test_a_stronger_compression_leaves_a_smaller_state() -> None:
    state = Json({"key": "value" * 1000}, path="data.json")
    sizes = [Gzip(state, compression=level).size for level in (1, 3, 9)]
    assert sizes == sorted(sizes, reverse=True)
    assert all(Gzip(state, compression=level).load().data == state.data for level in (1, 3, 9))


def test_a_compressed_state_is_a_plain_gzip_file() -> None:
    assert gzip.decompress(Gzip(SOURCE).data) == SOURCE.data


def test_compressing_the_same_payload_twice_gives_the_same_bytes() -> None:
    """No timestamp of its own leaks into the compressed bytes, which a gzip header has room for."""
    assert Gzip(SOURCE).data == Gzip(SOURCE).data


def test_a_gzip_file_written_elsewhere_is_read_as_a_layer() -> None:
    state = Gzip(Data(gzip.compress(b"payload")), path="data.txt.gz")
    inner = state.load()
    assert inner.path == "data.txt"
    assert inner.data == b"payload"


# encrypting


DOCUMENT = {"key": "value"}

#: two records of one storage, of which an onlooker is taken to know the first
FIRST = "attack at dawn, the code is 1234"
SECOND = "retreat at dusk, the code is 9999"


def _xor(left: bytes, right: bytes) -> bytes:
    return bytes(first ^ second for first, second in zip(left, right, strict=False))


@pytest.fixture(name="sealed", scope="module")
def sealed_fixture() -> Enc:
    """A document sealed under `PASSWORD` and `SALT`, sealed once for every test below."""
    return Json(DOCUMENT, path="document.json").encrypt(password=PASSWORD, salt=SALT)


def test_an_encrypted_state_is_opened_by_the_password_it_was_sealed_with(sealed: Enc) -> None:
    assert sealed.path == "document.json.enc"
    inner: LoadedState[Any] = sealed.load(password=PASSWORD, salt=SALT)
    assert inner.name == "document.json"
    assert inner.load() == DOCUMENT


@pytest.mark.parametrize(
    ("password", "salt"),
    [(PASSWORD, ""), ("password", SALT), ("password", "")],
)
def test_neither_a_wrong_password_nor_a_wrong_salt_opens_a_state(
    sealed: Enc,
    password: str,
    salt: str,
) -> None:
    with pytest.raises(ValueError, match="Decryption failed"):
        sealed.load(password=password, salt=salt)


def test_a_state_is_sealed_differently_every_time_it_is_sealed(sealed: Enc) -> None:
    """Sealing the same payload twice must not give the same bytes."""
    document = Json(DOCUMENT, path="document.json")
    assert sealed.data != document.encrypt(password=PASSWORD, salt=SALT).data


def test_two_states_sealed_with_one_password_do_not_share_a_keystream() -> None:
    """Two records of one storage must not give each other away.

    Covered by one keystream, two ciphertexts differ by exactly what their payloads differ by.
    """
    backend = MemoryStorage()
    storage = StateStorage(backend, password=PASSWORD, salt=SALT)
    storage.push("first.txt", FIRST)
    storage.push("second.txt", SECOND)

    # all an onlooker has is the two sealed records, and the payload of the one they know
    keystream = _xor(backend.pull("first.txt.enc"), FIRST.encode())
    stolen = _xor(backend.pull("second.txt.enc"), keystream)
    assert stolen != SECOND.encode()[: len(stolen)]


@pytest.mark.parametrize(
    "damage",
    [b"", b"tampered", b"\x00" * 64],
    ids=["cut", "swapped", "wiped"],
)
def test_a_sealed_state_that_was_meddled_with_is_refused(sealed: Enc, damage: bytes) -> None:
    """The seal vouches for the bytes, so what came back changed does not open at all."""
    meddled: LoadedState[Any] = LoadedState(damage + bytes(sealed.data)[8:], path=sealed.path)
    with pytest.raises(ValueError, match="Decryption failed"):
        Enc.from_state(meddled).load(password=PASSWORD, salt=SALT)
