__all__ = [
    "BinaryStorage",
    "Storage",
    "is_record_uid",
    "validate_uid",
]

from abc import ABC, abstractmethod
from collections.abc import Iterator
from io import BytesIO
from typing import BinaryIO, Generic, TypeVar

T = TypeVar("T")


def is_record_uid(uid: str) -> bool:
    """Tell whether a string is a uid a record could be handed back under.

    Args:
        uid: The string to read as the identifier of a record.

    Returns:
        Whether `uid` is a relative path whose parts are all names.

    """
    return bool(uid) and not any(part in {"", ".", ".."} for part in uid.split("/"))


def validate_uid(uid: str) -> tuple[str, ...]:
    """Split a record uid into the parts of the relative path it names.

    A uid is the name a record is handed back under, so it may only be what every storage can
    return unchanged: a relative path whose parts are all names. Anything a path would fold
    away, an empty uid included, names no record.

    Args:
        uid: The identifier of a record, a relative posix path.

    Returns:
        The parts of the path `uid` names, in order.

    Raises:
        ValueError: If `uid` is not a relative path naming a record.

    """
    if not is_record_uid(uid):
        msg = f"Record uid {uid!r} is not a relative path naming a record"
        raise ValueError(msg)
    return tuple(uid.split("/"))


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
