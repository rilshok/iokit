from iokit import Txt  # , load_file, save_temp


def test_txt_state() -> None:
    text = "Hello, World!\nThis is a test file."
    state = Txt(text, path="text.txt")
    assert state.name == "text.txt"
    assert state.stem == "text"
    assert state.load() == text
    assert state.size == len(text)


def test_txt_save_load_file() -> None:
    text = "Hello, World!"
    state = Txt(text, path="text.txt")
    with state.save_temp() as temp_state:
        assert temp_state.load() == text


def test_txt_state_japanese() -> None:
    text = "こんにちは、世界!\nこれはテストファイルです。"
    state = Txt(text, "text")
    assert state.load() == text
    assert state.size > len(text) * 2
