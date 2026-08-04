from iokit.utils.web import download


def test_download_file() -> None:
    uri = "https://raw.githubusercontent.com/rilshok/iokit/main/LICENSE"
    state = download(uri)
    assert "MIT License" in state.data.decode("utf-8")
