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
def test_a_state_is_filed_under_the_path_its_stem_and_format_make(
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
def test_a_name_that_says_two_things_at_once_is_refused(
    stem: str | None,
    path: str | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Json(DOCUMENT, stem, path)


def test_a_layer_takes_a_name_of_its_own_over_the_state_it_covers() -> None:
    """A layer carries bytes, so under a stem of its own it forgets the name it covered."""
    assert Gzip(Txt("payload", "data"), "data.txt").path == "data.txt.gz"

    packed = Gzip(Json(DOCUMENT, "greeting"), "backup")
    assert packed.path == "backup.gz"
    assert packed.load().path == "backup"

    # what a layer does to the payload it covers is in `tests/test_layer.py`; here it is the name
    sealed = Enc(Json(DOCUMENT, "greeting"), "secret", password=PASSWORD)
    assert sealed.path == "secret.enc"
    assert sealed.load(password=PASSWORD).path == "secret"


def test_a_layer_comes_off_an_extension_written_in_any_case() -> None:
    """A name that arrived shouting is still a name a layer can be taken off."""
    packed = Gzip(Txt("payload", "data"))
    state = Gzip.from_state(LoadedState(packed.data, path="DATA.TXT.GZ"))
    assert state.load().path == "DATA.TXT"


def test_a_state_is_renamed_where_it_lies() -> None:
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


def test_a_state_standing_for_a_file_refuses_to_be_renamed(tmp_path: Path) -> None:
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


def test_encoded_bytes_cannot_be_handed_a_codec_to_encode_them_again() -> None:
    """A state built from `Data` holds bytes that are already written; there is nothing to set."""
    with pytest.raises(ValueError, match="Cannot configure a codec"):
        Csv(Data(b"name,age\n"), path="table.csv", index=True)


@pytest.mark.parametrize("path", ["data.unknown", "noextension", "data.bin", ".secret"])
def test_a_name_no_format_claims_reads_back_as_the_bytes_it_is(path: str) -> None:
    """Raw bytes are what is left when nothing in the name says how to read them."""
    assert LoadedState(b"payload", path=path).load() == b"payload"


def test_a_name_is_matched_by_its_extension_whatever_case_it_is_written_in() -> None:
    """The longest known extension of the name wins, and it is read case-blind."""
    assert LoadedState(Json(DOCUMENT).data, path="GREETING.JSON").load() == DOCUMENT
    assert LoadedState(Json(DOCUMENT).data, path="greeting.backup.json").load() == DOCUMENT
