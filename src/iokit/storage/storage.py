__all__ = [
    "Storage",
    "ReadOnlyStorage",
]

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Generic, TypeVar


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
        pass

    def remove(self, uid: str) -> None:
        pass

    def exists(self, uid: str) -> bool:
        return self._storage.exists(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        return self._storage.index(prefix)
