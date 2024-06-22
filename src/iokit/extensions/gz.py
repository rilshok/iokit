import gzip
from io import BytesIO
from typing import Any

from iokit.state import State


class Gzip(State, suffix="gz"):
    def __init__(self, state: State, *, compression: int = 1, **kwargs: Any):
        data = BytesIO()
        gzip_file = gzip.GzipFile(fileobj=data, mode="wb", compresslevel=compression, mtime=0)
        with gzip_file as gzip_buffer:
            gzip_buffer.write(state.data.getvalue())
        super().__init__(data=data, name=state.name, **kwargs)

    def load(self) -> State:
        gzip_file = gzip.GzipFile(fileobj=self.data, mode="rb")
        with gzip_file as file:
            data = file.read()
        return State(data=data, name=str(self.name).removesuffix(".gz")).cast()
