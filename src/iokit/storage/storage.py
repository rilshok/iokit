__all__ = [
    "BinaryStorage",
    "Storage",
]

from abc import ABC, abstractmethod
from collections.abc import Iterator
from io import BytesIO
from typing import BinaryIO, Generic, TypeVar

T = TypeVar("T")


class Storage(ABC, Generic[T]):
    @abstractmethod
    def pull(self, uid: str) -> T:
        msg = "Method 'pull' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def push(self, uid: str, record: T, *, force: bool = False) -> None:
        msg = "Method 'push' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def remove(self, uid: str) -> None:
        msg = "Method 'remove' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def exists(self, uid: str) -> bool:
        msg = "Method 'exists' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def size(self, uid: str) -> int:
        msg = "Method 'size' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def index(self, prefix: str | None = None) -> Iterator[str]:
        msg = "Method 'index' must be implemented in a subclass"
        raise NotImplementedError(msg)


class BinaryStorage(Storage[bytes]):
    def __init__(self, backend: Storage[BinaryIO]) -> None:
        super().__init__()
        self._backend = backend

    def pull(self, uid: str) -> bytes:
        with self._backend.pull(uid) as buffer:
            return buffer.read()

    def push(self, uid: str, record: bytes, *, force: bool = False) -> None:
        with BytesIO(record) as buffer:
            return self._backend.push(uid, buffer, force=force)

    def remove(self, uid: str) -> None:
        self._backend.remove(uid)

    def exists(self, uid: str) -> bool:
        return self._backend.exists(uid)

    def size(self, uid: str) -> int:
        return self._backend.size(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        return self._backend.index(prefix)
