from iokit import Txt, Zip, first


def test_zip_state() -> None:
    state1 = Txt("First file", stem="text1")
    state2 = Txt("Second file", stem="text2")
    archive = Zip([state1, state2], stem="archive")
    assert archive.name == "archive.zip"
    assert archive.stem == "archive"
    assert archive.extension() == ".zip"
    states = list(archive.load())
    assert len(states) == 2
    assert first(states, "text1.txt").load() == "First file"
    assert first(states, "text2.txt").load() == "Second file"
