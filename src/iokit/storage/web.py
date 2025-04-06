__all__ = ["download_file"]

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, overload
from urllib.parse import urlparse

import requests
from dateutil.parser import parse as datetimeparse

from iokit.state import ExpectedStateType, State

if TYPE_CHECKING:
    from datetime import datetime

S = TypeVar("S", bound=State)


@overload
def download_file(
    url: str,
    expected_type: ExpectedStateType[S],
    *,
    timeout: int = 60,
    keep_path: bool = False,
) -> S: ...


@overload
def download_file(
    url: str,
    expected_type: None = None,
    *,
    timeout: int = 60,
    keep_path: bool = False,
) -> State: ...


def download_file(
    url: str,
    expected_type: ExpectedStateType[S] | None = None,
    *,
    timeout: int = 60,
    keep_path: bool = False,
) -> S | State:
    response = requests.get(url, timeout=timeout)
    if not response.ok:
        msg = f"Failed to download file: uri='{url}', status_code={response.status_code}"
        raise FileNotFoundError(msg)

    mtime_str = response.headers.get("Last-Modified")
    mtime: datetime | None = None
    if mtime_str is not None:
        with suppress(Exception):
            mtime = datetimeparse(mtime_str)

    name = urlparse(url).path
    if not keep_path:
        name = Path(name).name

    return State(response.content, name=name, time=mtime).cast(expected_type)
