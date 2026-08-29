"""Abstract storage interface for records."""

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
    """Check if a string is a valid record identifier.

    Args:
        uid: String to validate.

    Returns:
        True if `uid` is a valid record identifier.

    """
    return bool(uid) and not any(part in {"", ".", ".."} for part in uid.split("/"))


def validate_uid(uid: str) -> tuple[str, ...]:
    """Split a record identifier into path parts.

    Args:
        uid: Record identifier as relative POSIX path.

    Returns:
        Path parts that `uid` represents.

    Raises:
        ValueError: If `uid` is not a valid record identifier.

    """
    if not is_record_uid(uid):
        msg = f"Record uid {uid!r} is not a relative path naming a record"
        raise ValueError(msg)
    return tuple(uid.split("/"))


class Storage(ABC, Generic[T]):
    """Abstract base class for record storage backends."""

    @abstractmethod
    def pull(self, uid: str) -> T:
        """Retrieve a record by identifier.

        Args:
            uid: Record identifier.

        Returns:
            The record.

        Raises:
            NotImplementedError: Must be implemented by subclasses.

        """
        msg = "Method 'pull' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def push(self, uid: str, record: T, *, force: bool = False) -> None:
        """Store a record.

        Args:
            uid: Record identifier.
            record: Record to store.
            force: Overwrite existing record.

        Raises:
            NotImplementedError: Must be implemented by subclasses.

        """
        msg = "Method 'push' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def remove(self, uid: str) -> None:
        """Delete a record.

        Args:
            uid: Record identifier.

        Raises:
            NotImplementedError: Must be implemented by subclasses.

        """
        msg = "Method 'remove' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def exists(self, uid: str) -> bool:
        """Check if a record exists.

        Args:
            uid: Record identifier.

        Returns:
            True if record exists.

        Raises:
            NotImplementedError: Must be implemented by subclasses.

        """
        msg = "Method 'exists' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def size(self, uid: str) -> int:
        """Get record size in bytes.

        Args:
            uid: Record identifier.

        Returns:
            Size in bytes.

        Raises:
            NotImplementedError: Must be implemented by subclasses.

        """
        msg = "Method 'size' must be implemented in a subclass"
        raise NotImplementedError(msg)

    @abstractmethod
    def index(self, prefix: str | None = None) -> Iterator[str]:
        """Yield record identifiers, optionally filtered by prefix.

        Args:
            prefix: Filter by prefix, or `None` for all.

        Yields:
            Record identifiers.

        Raises:
            NotImplementedError: Must be implemented by subclasses.

        """
        msg = "Method 'index' must be implemented in a subclass"
        raise NotImplementedError(msg)


class BinaryStorage(Storage[bytes]):
    """Storage adapter that handles binary data."""

    def __init__(self, backend: Storage[BinaryIO]) -> None:
        """Initialize with a binary I/O backend.

        Args:
            backend: Binary I/O storage backend.

        """
        super().__init__()
        self._backend = backend

    def pull(self, uid: str) -> bytes:
        """Retrieve binary data.

        Args:
            uid: Record identifier.

        Returns:
            The data as bytes.

        """
        with self._backend.pull(uid) as buffer:
            return buffer.read()

    def push(self, uid: str, record: bytes, *, force: bool = False) -> None:
        """Store binary data.

        Args:
            uid: Record identifier.
            record: Binary data to store.
            force: Overwrite existing record.

        """
        with BytesIO(record) as buffer:
            return self._backend.push(uid, buffer, force=force)

    def remove(self, uid: str) -> None:
        """Delete binary data.

        Args:
            uid: Record identifier.

        """
        self._backend.remove(uid)

    def exists(self, uid: str) -> bool:
        """Check if binary data exists.

        Args:
            uid: Record identifier.

        Returns:
            True if record exists.

        """
        return self._backend.exists(uid)

    def size(self, uid: str) -> int:
        """Get size of binary data in bytes.

        Args:
            uid: Record identifier.

        Returns:
            Size in bytes.

        """
        return self._backend.size(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """Yield record identifiers, optionally filtered by prefix.

        Args:
            prefix: Filter by prefix, or `None` for all.

        Yields:
            Record identifiers.

        """
        return self._backend.index(prefix)
