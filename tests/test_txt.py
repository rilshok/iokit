from iokit import Txt, load_file, save_temp


def test_txt_state() -> None:
    text = "Hello, World!\nThis is a test file."
    state = Txt(text, name="text")
    assert state.name == "text.txt"
    assert state.name.stem == "text"
    assert state.name.suffix == "txt"
    assert state.load() == text
    assert state.size == len(text)


def test_txt_save_load_file() -> None:
    text = "Hello, World!"
    state = Txt(text, name="text")
    with save_temp(state) as path:
        assert load_file(path).load() == text


def test_txt_state_japanese() -> None:
    text = "こんにちは、世界！\nこれはテストファイルです。"
    state = Txt(text, name="text")
    assert state.load() == text
    assert state.size > len(text) * 2
