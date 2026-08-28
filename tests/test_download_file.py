import pytest

from iokit.utils.web import web

#: reaching the raw content of the repository itself, so the test needs the network to pass
pytestmark = pytest.mark.network


def test_download() -> None:
    uri = "https://raw.githubusercontent.com/rilshok/iokit/main/LICENSE"
    state = web(uri)
    assert "MIT License" in state.data.decode("utf-8")
