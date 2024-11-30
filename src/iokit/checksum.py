__all__ = [
    "hexdigest_xxh128",
    "hexdigest_sha256",
    "hexdigest_md5",
    "hexdigest_sha1",
]

import hashlib
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from io import BytesIO
from typing import Any

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


def _iterate_chuncks(
    data: Data,
    chunk_size: int = CHUNK_SIZE,
) -> Iterator[bytes]:
    with _buffer(data) as buffer:
        yield from iter(lambda: buffer.read(chunk_size), b"")


def _hexdigest(algorithm: Any, data: Data) -> str:
    for chunk in _iterate_chuncks(data):
        algorithm.update(chunk)
    return algorithm.hexdigest()


def hexdigest_xxh128(data: Data) -> str:
    return _hexdigest(algorithm=xxhash.xxh128(), data=data)


def hexdigest_sha256(data: Data) -> str:
    return _hexdigest(algorithm=hashlib.sha256(), data=data)


def hexdigest_md5(data: Data) -> str:
    return _hexdigest(algorithm=hashlib.md5(), data=data)


def hexdigest_sha1(data: Data) -> str:
    return _hexdigest(algorithm=hashlib.sha1(), data=data)
