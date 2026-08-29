"""Storage wrapper that caches reads from a backend."""

__all__ = [
    "CachedStorage",
]

from collections.abc import Iterator
from typing import TypeVar

from .storage import Storage

T = TypeVar("T")


class CachedStorage(Storage[T]):
    """Cache reads and writes to a fast storage in front of a slow one."""

    def __init__(self, hot: Storage[T], cold: Storage[T]) -> None:
        """Initialize cached storage with hot and cold backends.

        Args:
            hot: Fast storage layer.
            cold: Slow storage layer serving as source of truth.

        """
        super().__init__()
        self._hot = hot
        self._cold = cold

    def pull(self, uid: str) -> T:
        """Read a record, caching it in hot storage if needed.

        Args:
            uid: Record identifier.

        Returns:
            The record from hot storage.

        Raises:
            FileNotFoundError: If the record is not in either storage.

        """
        if not self._hot.exists(uid):
            self._hot.push(uid, self._cold.pull(uid), force=True)
        return self._hot.pull(uid)

    def push(self, uid: str, record: T, *, force: bool = False) -> None:
        """Write a record to both storages.

        Args:
            uid: Record identifier.
            record: Record to store.
            force: Overwrite existing record.

        Raises:
            FileExistsError: If the record already exists and `force` is not set.

        """
        if not force and self.exists(uid):
            msg = f"Record with uid {uid!r} already exists"
            raise FileExistsError(msg)
        self._hot.push(uid, record, force=True)
        try:
            self._cold.push(uid, self._hot.pull(uid), force=True)
        except Exception:
            # a record the cold storage never took must not be left behind in the cache
            self._hot.remove(uid)
            raise

    def remove(self, uid: str) -> None:
        """Remove a record from both storages.

        Args:
            uid: Record identifier.

        Raises:
            FileNotFoundError: If the record does not exist in either storage.

        """
        found = False
        for storage in (self._hot, self._cold):
            if storage.exists(uid):
                storage.remove(uid)
                found = True
        if not found:
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg)

    def exists(self, uid: str) -> bool:
        """Check if a record exists in either storage.

        Args:
            uid: Record identifier.

        Returns:
            True if the record exists in hot or cold storage.

        """
        return self._hot.exists(uid) or self._cold.exists(uid)

    def size(self, uid: str) -> int:
        """Return the size of a record from hot storage if available, else cold.

        Args:
            uid: Record identifier.

        Returns:
            Size of the record in bytes.

        Raises:
            FileNotFoundError: If the record does not exist in either storage.

        """
        if self._hot.exists(uid):
            return self._hot.size(uid)
        return self._cold.size(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """Yield all record identifiers from cold storage.

        Args:
            prefix: Filter yielded identifiers by prefix, or `None` for all.

        Yields:
            Record identifiers in cold storage.

        """
        return self._cold.index(prefix)
