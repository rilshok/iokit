from iokit import Txt, Zip, find_state


def test_zip_state() -> None:
    state1 = Txt("First file", name="text1")
    state2 = Txt("Second file", name="text2")
    archive = Zip([state1, state2], name="archive")
    assert archive.name == "archive.zip"
    assert archive.name.stem == "archive"
    assert archive.name.suffix == "zip"
    assert archive.name.suffixes == ("zip",)
    states = list(archive.load())
    assert len(states) == 2
    assert find_state(states, "text1.txt").load() == "First file"
    assert find_state(states, "text2.txt").load() == "Second file"
