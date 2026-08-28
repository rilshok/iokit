from iokit import Gzip, Tar, Txt, first


def test_tar_state() -> None:
    state1 = Txt("First file", stem="text1")
    state2 = Txt("Second file", stem="text2")
    archive = Tar([state1, state2], stem="archive")
    assert archive.name == "archive.tar"
    assert archive.stem == "archive"
    assert archive.extension() == ".tar"
    states = archive.load()
    assert first(states, "text1.txt").load() == "First file"
    assert first(states, "text2.txt").load() == "Second file"


def test_a_compressed_tar_unpacks_to_the_states_it_was_packed_from() -> None:
    archive = Tar([Txt("First file", stem="text1"), Txt("Second file", stem="text2")], stem="a")
    loaded = Gzip(archive).load().load()
    assert first(loaded, "text1.txt").load() == "First file"
    assert first(loaded, "text2.txt").load() == "Second file"
