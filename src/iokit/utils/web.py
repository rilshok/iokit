"""Download data from HTTP URLs into state objects."""

__all__ = ["web"]

from contextlib import suppress
from pathlib import Path
from typing import Any, TypeVar, overload
from urllib.parse import urlparse

import requests
from dateutil.parser import parse as datetimeparse

from iokit.state import FormatState, LoadedState
from iokit.utils.time import Timestamp

F = TypeVar("F", bound=FormatState[Any])


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
    """Download a file as a state with URL path.

    Args:
        url: URL to fetch.
        expected_type: Expected format; extension verified against path.
        timeout: Response timeout in seconds.
        keep_path: Use full URL path instead of just filename.

    Returns:
        The downloaded state, timestamped from server.

    """
    response = requests.get(url, timeout=timeout)
    if not response.ok:
        msg = f"Failed to download file: uri='{url}', status_code={response.status_code}"
        raise FileNotFoundError(msg)

    timestamp: float | None = None
    mtime = response.headers.get("Last-Modified")
    if mtime is not None:
        with suppress(Exception):
            timestamp = Timestamp.from_datetime(datetimeparse(mtime))

    path = urlparse(url).path
    if not keep_path:
        path = Path(path).name

    state: LoadedState[Any] = LoadedState(response.content, path=path, timestamp=timestamp)
    if expected_type is None:
        return state
    return expected_type.from_state(state)
