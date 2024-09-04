__all__ = [
    "download_file",
]

from contextlib import suppress
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from dateutil.parser import parse as datetimeparse

from iokit.state import State


def download_file(url: str, *, timeout: int = 60, keep_path: bool = False) -> State:
    resopnse = requests.get(url, timeout=timeout)
    if not resopnse.ok:
        msg = f"Failed to download file: uri='{url}', status_code={resopnse.status_code}"
        raise FileNotFoundError(msg)

    mtime_str = resopnse.headers.get("Last-Modified")
    mtime: datetime | None = None
    if mtime_str is not None:
        with suppress(Exception):
            mtime = datetimeparse(mtime_str)

    name = urlparse(url).path
    if not keep_path:
        name = Path(name).name

    return State(data=resopnse.content, name=name, time=mtime)
