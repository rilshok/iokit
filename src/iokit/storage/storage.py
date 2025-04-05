__all__ = [
    "Storage",
    "ReadOnlyStorage",
]

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Generic, TypeVar
import warnings


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
    def index(self, prefix: str | None = None) -> Iterator[str]:
        msg = "Method 'index' must be implemented in a subclass"
        raise NotImplementedError(msg)


class BackendStorage(Storage[bytes]):
    pass


class ReadOnlyStorage(Storage[T]):
    def __init__(self, storage: Storage[T]):
        self._storage = storage

    def pull(self, uid: str) -> T:
        return self._storage.pull(uid)

    def push(self, uid: str, record: T, *, force: bool = False) -> None:
        force_str = f"{force} " if force else ""
        record_repr = repr(record)
        record_repr = record_repr if len(record_repr) < 30 else f"{type(record)}"
        msg = f"Attempt to {force_str}push to read-only storage: {uid=}, {record_repr}"
        warnings.warn(msg, stacklevel=2)

    def remove(self, uid: str) -> None:
        msg = f"Attempt to remove from read-only storage: {uid}"
        warnings.warn(msg, stacklevel=2)

    def exists(self, uid: str) -> bool:
        return self._storage.exists(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        return self._storage.index(prefix)
