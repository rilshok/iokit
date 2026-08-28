"""What an archive holds: whole states, handed back under the paths they were packed with.

An archive is a state like any other, so the states it holds keep what a state has: where it
goes, and when it was last touched. Packing a folder and unpacking it elsewhere has to give
back what went in, down to the directories the members were sitting in.
"""

import pytest

from iokit import Archive, Gzip, Tar, Txt, Zip

MEMBERS = [Txt("First file", stem="text1"), Txt("Second file", stem="text2")]

#: two files of the same name, from two directories - the everyday shape of a packed folder
TREE = [
    Txt("of 2024", path="reports/2024/summary.txt"),
    Txt("of 2025", path="reports/2025/summary.txt"),
]

TOUCHED = 1_000_000_000


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_an_archive_is_named_the_way_a_state_of_its_format_is(kind: type[Archive]) -> None:
    archive = kind(MEMBERS, stem="archive")
    assert archive.name == "archive" + kind.extension()
    assert archive.stem == "archive"


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_an_archive_unpacks_to_the_states_it_was_packed_from(kind: type[Archive]) -> None:
    unpacked = {state.path: state.load() for state in kind(MEMBERS, stem="archive").load()}
    assert unpacked == {"text1.txt": "First file", "text2.txt": "Second file"}


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_a_compressed_archive_unpacks_the_same_way(kind: type[Archive]) -> None:
    """A layer over an archive comes off without the members noticing."""
    archive = Gzip(kind(MEMBERS, stem="archive"))
    unpacked = {state.path: state.load() for state in archive.load().load()}
    assert unpacked == {"text1.txt": "First file", "text2.txt": "Second file"}


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_a_member_is_packed_under_the_whole_path_it_carries(kind: type[Archive]) -> None:
    """The directories a member sits in are part of where it goes, so an archive carries them.

    Dropping them does not merely flatten a tree: two files of the same name from two
    directories become one name, and what unpacks under it is no longer what was packed.
    """
    unpacked = {state.path: state.load() for state in kind(TREE, stem="archive").load()}
    assert unpacked == {
        "reports/2024/summary.txt": "of 2024",
        "reports/2025/summary.txt": "of 2025",
    }


@pytest.mark.parametrize("kind", [Tar, Zip])
def test_a_member_keeps_the_time_it_was_last_touched(kind: type[Archive]) -> None:
    """A state carries its timestamp, and being packed is not touching it."""
    member = Txt("First file", stem="text1", timestamp=TOUCHED)
    unpacked = next(iter(kind([member], stem="archive").load()))
    assert unpacked.timestamp == TOUCHED
