__all__ = ["Gzip"]

import gzip
from io import BytesIO
from typing import Any

from iokit.state import State


class Gzip(State, suffix="gz"):
    def __init__(self, content: State, /, *, compression: int = 1, **kwargs: Any) -> None:
        with BytesIO() as buffer:
            gzip_file = gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=compression, mtime=0)
            with gzip_file as gzip_buffer:
                gzip_buffer.write(content.data)
            super().__init__(buffer.getvalue(), name=content.name, **kwargs)

    def load(self) -> State:
        with gzip.GzipFile(fileobj=self.buffer, mode="rb") as file:
            return State(file.read(), name=str(self.name).removesuffix(".gz")).cast()
