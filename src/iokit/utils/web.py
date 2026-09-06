"""Download data from URLs into state objects."""

__all__ = ["web"]

from contextlib import suppress
from pathlib import Path
from typing import Any, TypeVar, overload
from urllib.parse import unquote, urlparse

from iokit.state import FormatState, LoadedState
from iokit.utils.dataurl import dataurl, is_dataurl
from iokit.utils.time import Timestamp

F = TypeVar("F", bound=FormatState[Any])


def _download(url: str, *, timeout: int, keep_path: bool) -> LoadedState[Any]:
    """Fetch `url` over HTTP, naming the state after the path it was served from."""
    import requests  # noqa: PLC0415  # only a URL of the network needs it installed
    from dateutil.parser import parse as datetimeparse  # noqa: PLC0415

    response = requests.get(url, timeout=timeout)
    if not response.ok:
        msg = f"Failed to download file: uri='{url}', status_code={response.status_code}"
        raise FileNotFoundError(msg)

    timestamp: float | None = None
    mtime = response.headers.get("Last-Modified")
    if mtime is not None:
        with suppress(Exception):
            timestamp = Timestamp.from_datetime(datetimeparse(mtime))

    path = unquote(urlparse(url).path)  # a name is escaped on the wire, not on disk
    if not keep_path:
        path = Path(path).name

    return LoadedState(response.content, path=path, timestamp=timestamp)


@overload
def web(
    url: str,
    expected_type: type[F],
    *,
    timeout: int = 60,
    keep_path: bool = False,
) -> F: ...


@overload
def web(
    url: str,
    expected_type: None = None,
    *,
    timeout: int = 60,
    keep_path: bool = False,
) -> LoadedState[Any]: ...


def web(
    url: str,
    expected_type: type[F] | None = None,
    *,
    timeout: int = 60,
    keep_path: bool = False,
) -> F | LoadedState[Any]:
    """Read a URL as a state, named after the path it was served from.

    A `data:` URL is decoded where it stands, without reaching the network and with
    nothing for `timeout` or `keep_path` to act on. It carries no name for its payload,
    so the state is left with the bare extension of its media type, `.json` or `.jpeg`.

    Args:
        url: URL to fetch, of the http, https, or data scheme.
        expected_type: Expected format; extension verified against path.
        timeout: Response timeout in seconds.
        keep_path: Use full URL path instead of just filename.

    Returns:
        The downloaded state, timestamped from server.

    Raises:
        FileNotFoundError: If the server answers with anything but success.
        ValueError: If a data URL is malformed, or the path lacks the extension of
            `expected_type`.

    """
    state = (
        dataurl(url) if is_dataurl(url) else _download(url, timeout=timeout, keep_path=keep_path)
    )
    if expected_type is None:
        return state
    return expected_type.from_state(state)
