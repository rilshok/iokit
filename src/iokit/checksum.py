__all__ = ["xxh128"]

from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO

import xxhash

from .state import State

Data = State | bytes | BytesIO

CHUNK_SIZE = 4096


@contextmanager
def _buffer(data: Data) -> Generator[BytesIO, None, None]:
    close = False
    if isinstance(data, State):
        buffer = data.buffer
        close = True
    elif isinstance(data, bytes):
        buffer = BytesIO(data)
        close = True
    else:
        buffer = data
        buffer.seek(0)

    try:
        yield buffer

    finally:
        if close:
            buffer.close()


def xxh128(data: Data) -> str:
    hash_object = xxhash.xxh128()
    with _buffer(data) as buffer:
        for chunk in iter(lambda: buffer.read(CHUNK_SIZE), b""):
            hash_object.update(chunk)
        file_hash = hash_object.hexdigest()
        return file_hash
