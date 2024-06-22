from iokit import Gzip, Tar, Txt, find_state


def test_tar_state() -> None:
    state1 = Txt("First file", name="text1")
    state2 = Txt("Second file", name="text2")
    archive = Tar([state1, state2], name="archive")
    assert archive.name == "archive.tar"
    assert archive.name.stem == "archive"
    assert archive.name.suffix == "tar"
    assert archive.name.suffixes == ("tar",)
    states = archive.load()
    assert find_state(states, "text1.txt").load() == "First file"
    assert find_state(states, "text2.txt").load() == "Second file"


def test_tar_compress() -> None:
    state1 = Txt("First file", name="text1")
    state2 = Txt("Second file", name="text2")
    archive = Tar([state1, state2], name="archive")
    archive1_gz = Gzip(archive)
    archive2_gz = Gzip(archive)

    assert archive1_gz.size == archive2_gz.size
    assert archive1_gz.data.getvalue() == archive2_gz.data.getvalue()
    loaded = archive1_gz.load().load()
    assert find_state(loaded, "text1.txt").load() == "First file"
    assert find_state(loaded, "text2.txt").load() == "Second file"
