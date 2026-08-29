"""What text is written as, over and above what every format owes in the contract."""

from iokit import Txt

TEXT = "こんにちは、世界!\nこれはテストファイルです。"


def test_text_is_written_as_utf_8() -> None:
    """The size counts the bytes of the encoding, not the characters of the text."""
    state = Txt(TEXT, stem="text")
    assert state.data == TEXT.encode("utf-8")
    assert state.size > len(TEXT) * 2
