"""How a state is named: the stem it is given, the extension its format adds, and the path.

A state is filed under a path, and the extension of that path is what says how to read the
payload back. The two can be given together, and what is here is what the one makes of the
other, and what is refused as saying two different things at once.
"""

from pathlib import Path

import pytest

from iokit import Enc, Gzip, Json, LoadedState, Txt

DOCUMENT = {"hello": "world"}


def test_stem_completes_the_key() -> None:
    state = Json(DOCUMENT, "greeting")
    assert state.path == "greeting.json"
    assert state.name == "greeting.json"
    assert state.stem == "greeting"
    assert state.load() == DOCUMENT


def test_stem_keeps_the_directories_it_carries() -> None:
    state = Json(DOCUMENT, "nested/dir/greeting")
    assert state.path == "nested/dir/greeting.json"
    assert state.name == "greeting.json"


def test_key_alone_is_taken_as_it_stands() -> None:
    assert Json(DOCUMENT, path="greeting.json").path == "greeting.json"


def test_stem_and_key_agreeing_are_both_allowed() -> None:
    assert Json(DOCUMENT, "greeting", "greeting.json").path == "greeting.json"
    assert Json(DOCUMENT, "greeting", "nested/greeting.json").path == "nested/greeting.json"
    assert Json(DOCUMENT, "nested/greeting", "nested/greeting.json").path == "nested/greeting.json"


def test_stem_disagreeing_with_the_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="does not match the path"):
        Json(DOCUMENT, "greeting", "farewell.json")


def test_a_state_of_no_name_is_filed_under_the_bare_extension() -> None:
    state = Json(DOCUMENT)
    assert state.path == ".json"
    assert state.name == ".json"
    assert state.load() == DOCUMENT


def test_a_stem_carrying_the_extension_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"already carries the '\.json' extension"):
        Json(DOCUMENT, "greeting.json")


def test_a_key_without_the_extension_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"must end with '\.json'"):
        Json(DOCUMENT, path="greeting.yaml")


def test_a_stem_may_carry_another_extension() -> None:
    assert Gzip(Txt("payload", "data"), "data.txt").path == "data.txt.gz"


def test_save_under_a_stem(tmp_path: Path) -> None:
    state = Json(DOCUMENT, "greeting").save(tmp_path)
    assert Path(state.path).resolve() == tmp_path / "greeting.json"
    assert state.load() == DOCUMENT


def test_compressing_under_a_stem() -> None:
    state = Gzip(Json(DOCUMENT, "greeting"), "backup")
    assert state.path == "backup.gz"
    # the layer carries nothing of the state it holds, so it comes back under its own path
    assert state.load().path == "backup"


def test_encrypting_under_a_stem() -> None:
    state = Enc(Json(DOCUMENT, "greeting"), "secret", password="pA$sw0Rd")
    assert state.path == "secret.enc"
    assert state.load(password="pA$sw0Rd").data == Json(DOCUMENT, "greeting").data


def test_setting_the_name_renames_the_state_where_it_lies() -> None:
    state = Json(DOCUMENT, "nested/dir/greeting")
    state.name = "farewell.json"
    assert state.path == "nested/dir/farewell.json"
    assert state.load() == DOCUMENT


def test_setting_the_stem_keeps_the_extension() -> None:
    state = Json(DOCUMENT, "nested/dir/greeting")
    state.stem = "farewell"
    assert state.path == "nested/dir/farewell.json"


def test_a_state_standing_for_a_file_refuses_to_be_renamed(tmp_path: Path) -> None:
    state = Json(DOCUMENT, "greeting").save(tmp_path)
    for attribute, value in (("path", "other.json"), ("name", "other.json"), ("stem", "other")):
        with pytest.raises(AttributeError, match="Cannot rename a state standing for a file"):
            setattr(state, attribute, value)
    assert state.load() == DOCUMENT


def test_an_empty_stem_given_alongside_a_path_is_caught() -> None:
    # left out is not the same as given empty: an empty stem came from somewhere
    with pytest.raises(ValueError, match="does not match the path"):
        Json(DOCUMENT, "", "greeting.json")


def test_the_suffix_is_what_the_name_carries_past_its_stem() -> None:
    state = Json(DOCUMENT, "nested/dir/greeting")
    assert state.suffix == Json.extension() == ".json"
    assert state.name == state.stem + state.suffix
    state.suffix = ".txt"
    assert state.path == "nested/dir/greeting.txt"


def test_a_state_standing_for_a_file_refuses_a_new_suffix(tmp_path: Path) -> None:
    state = Json(DOCUMENT, "greeting").save(tmp_path)
    with pytest.raises(AttributeError, match="Cannot rename a state standing for a file"):
        state.suffix = ".txt"


def test_a_layer_comes_off_an_extension_written_in_any_case() -> None:
    packed = Gzip(Txt("payload", "data"))
    state = Gzip.from_state(LoadedState(packed.data, path="DATA.TXT.GZ"))
    assert state.load().path == "DATA.TXT"


def test_a_stem_given_as_the_whole_name_says_what_the_stem_would_be() -> None:
    with pytest.raises(ValueError, match="whose stem is 'greeting'"):
        Json(DOCUMENT, "greeting.json", "greeting.json")


def test_a_stem_may_carry_the_extension_when_the_path_doubles_it() -> None:
    assert Json(DOCUMENT, "greeting.json", "greeting.json.json").path == "greeting.json.json"
