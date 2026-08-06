from iokit.utils.web import web


def test_download() -> None:
    uri = "https://raw.githubusercontent.com/rilshok/iokit/main/LICENSE"
    state = web(uri)
    assert "MIT License" in state.data.decode("utf-8")
