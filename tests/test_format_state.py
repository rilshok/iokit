"""How a state is named: the stem it is given, the extension its format adds, and the path.

A stem is a path with the extension left off, so the two may be given together and have to agree.
"""

from pathlib import Path

import pytest

from iokit import Csv, Data, Enc, Gzip, Json, LoadedState, Txt

PASSWORD = "pA$sw0Rd"  # noqa: S105
DOCUMENT = {"hello": "world"}


@pytest.mark.parametrize(
    ("stem", "path", "expected"),
    [
        ("greeting", None, "greeting.json"),
        # a stem carries the directories it is written with
        ("nested/dir/greeting", None, "nested/dir/greeting.json"),
        # a path is taken as it stands, extension and all
        (None, "greeting.json", "greeting.json"),
        # given together they have to agree, and then either may carry the directories
        ("greeting", "greeting.json", "greeting.json"),
        ("greeting", "nested/greeting.json", "nested/greeting.json"),
        ("nested/greeting", "nested/greeting.json", "nested/greeting.json"),
        # a stem may end in the extension when the path really does double it
        ("greeting.json", "greeting.json.json", "greeting.json.json"),
        # named by neither, a state is filed under the bare extension of its format
        (None, None, ".json"),
    ],
)
def test_path_from_stem_and_format(
    stem: str | None,
    path: str | None,
    expected: str,
) -> None:
    state = Json(DOCUMENT, stem, path)
    assert state.path == expected
    assert state.load() == DOCUMENT


@pytest.mark.parametrize(
    ("stem", "path", "message"),
    [
        # a stem and a path that name two different states
        ("greeting", "farewell.json", "does not match the path"),
        # left out is not the same as given empty: an empty stem came from somewhere
        ("", "greeting.json", "does not match the path"),
        # a stem is a name without the extension, which the format is there to add
        ("greeting.json", None, r"already carries the '\.json' extension"),
        ("greeting.json", "greeting.json", "whose stem is 'greeting'"),
        # a path that promises another format than the one asked to write it
        (None, "greeting.yaml", r"must end with '\.json'"),
    ],
)
def test_contradictory_name_refused(
    stem: str | None,
    path: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Json(DOCUMENT, stem, path)


def test_layer_under_its_own_stem() -> None:
    """A layer carries bytes, so under a stem of its own it forgets the name it covered."""
    assert Gzip(Txt("payload", "data"), "data.txt").path == "data.txt.gz"

    packed = Gzip(Json(DOCUMENT, "greeting"), "backup")
    assert packed.path == "backup.gz"
    assert packed.load().path == "backup"

    # what a layer does to the payload it covers is in `tests/test_layer.py`; here it is the name
    sealed = Enc(Json(DOCUMENT, "greeting"), "secret", password=PASSWORD)
    assert sealed.path == "secret.enc"
    assert sealed.load(password=PASSWORD).path == "secret"


def test_layer_off_an_uppercase_name() -> None:
    """A name that arrived shouting is still a name a layer can be taken off."""
    packed = Gzip(Txt("payload", "data"))
    state = Gzip.from_state(LoadedState(packed.data, path="DATA.TXT.GZ"))
    assert state.load().path == "DATA.TXT"


def test_renaming_a_state() -> None:
    """Name, stem and suffix are three ways at the path, and none of them moves the state."""
    state = Json(DOCUMENT, "nested/dir/greeting")
    assert state.suffix == Json.extension() == ".json"
    assert state.name == state.stem + state.suffix

    state.name = "farewell.json"
    assert state.path == "nested/dir/farewell.json"
    state.stem = "greeting"
    assert state.path == "nested/dir/greeting.json"
    assert state.load() == DOCUMENT

    # the suffix is what says how to read the bytes back, so renaming over it reads them anew
    state.suffix = ".txt"
    assert state.path == "nested/dir/greeting.txt"
    assert state.load() == '{"hello": "world"}'


def test_a_file_state_refuses_renaming(tmp_path: Path) -> None:
    """The name of a saved state is the name of the file, which renaming would not move."""
    state = Json(DOCUMENT, "greeting").save(tmp_path)
    assert Path(state.path).resolve() == tmp_path / "greeting.json"
    for attribute, value in (
        ("path", "other.json"),
        ("name", "other.json"),
        ("stem", "other"),
        ("suffix", ".txt"),
    ):
        with pytest.raises(AttributeError, match="Cannot rename a state standing for a file"):
            setattr(state, attribute, value)
    assert state.load() == DOCUMENT


def test_codec_config_on_encoded_bytes() -> None:
    """A state built from `Data` holds bytes that are already written; there is nothing to set."""
    with pytest.raises(ValueError, match="Cannot configure a codec"):
        Csv(Data(b"name,age\n"), path="table.csv", index=True)


@pytest.mark.parametrize("path", ["data.unknown", "noextension", "data.bin", ".secret"])
def test_unclaimed_name_reads_as_bytes(path: str) -> None:
    """Raw bytes are what is left when nothing in the name says how to read them."""
    assert LoadedState(b"payload", path=path).load() == b"payload"


def test_extension_match_is_case_blind() -> None:
    """The longest known extension of the name wins, and it is read case-blind."""
    assert LoadedState(Json(DOCUMENT).data, path="GREETING.JSON").load() == DOCUMENT
    assert LoadedState(Json(DOCUMENT).data, path="greeting.backup.json").load() == DOCUMENT
