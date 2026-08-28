"""What an archive holds: whole states, handed back under the names they were packed with."""

import pytest

from iokit import Archive, Gzip, Tar, Txt, Zip

MEMBERS = [Txt("First file", stem="text1"), Txt("Second file", stem="text2")]


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_an_archive_is_named_the_way_a_state_of_its_format_is(kind: type[Archive]) -> None:
    archive = kind(MEMBERS, stem="archive")
    assert archive.name == "archive" + kind.extension()
    assert archive.stem == "archive"


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_an_archive_unpacks_to_the_states_it_was_packed_from(kind: type[Archive]) -> None:
    unpacked = {state.name: state.load() for state in kind(MEMBERS, stem="archive").load()}
    assert unpacked == {"text1.txt": "First file", "text2.txt": "Second file"}


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_a_compressed_archive_unpacks_the_same_way(kind: type[Archive]) -> None:
    """A layer over an archive comes off without the members noticing."""
    archive = Gzip(kind(MEMBERS, stem="archive"))
    unpacked = {state.name: state.load() for state in archive.load().load()}
    assert unpacked == {"text1.txt": "First file", "text2.txt": "Second file"}
