from iokit import download_file


def test_download_file():
    uri = "https://raw.githubusercontent.com/rilshok/iokit/main/LICENSE"
    state = download_file(uri)
    assert "MIT License" in state.data.getvalue().decode("utf-8")
