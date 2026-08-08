__all__ = [
    "CachedStorage",
]

from collections.abc import Iterator
from typing import TypeVar

from .storage import Storage

T = TypeVar("T")


class CachedStorage(Storage[T]):
    """A fast storage kept in front of a slow one, holding whatever has been read or written.

    The cold storage is the source of truth: every record that reaches the hot storage is
    written to the cold one as well, so a record found in the cache is known to be stored.
    That invariant is what lets `exists` and `size` answer from the hot storage alone,
    without ever asking the cold one, while `index` always walks the cold storage.

    Records travel between the two as whatever type the storages hold, and a record pulled
    from the cold storage is handed straight to the hot one. Streams are therefore consumed
    by the caching push, and what the caller gets back is always read from the hot storage.
    """

    def __init__(self, hot: Storage[T], cold: Storage[T]) -> None:
        super().__init__()
        self._hot = hot
        self._cold = cold

    def pull(self, uid: str) -> T:
        """Read a record back, caching it in the hot storage if it was not there yet.

        Args:
            uid: The identifier the record is stored under.

        Returns:
            The record, always as the hot storage holds it.

        Raises:
            FileNotFoundError: If neither storage holds a record under `uid`.

        """
        if not self._hot.exists(uid):
            self._hot.push(uid, self._cold.pull(uid), force=True)
        return self._hot.pull(uid)

    def push(self, uid: str, record: T, *, force: bool = False) -> None:
        """Write a record to both storages, the hot one first.

        Args:
            uid: The identifier to store the record under.
            record: The record to store.
            force: Whether to overwrite a record already stored under `uid`.

        Raises:
            FileExistsError: If a record is stored under `uid` and `force` is not set.

        """
        if not force and self.exists(uid):
            msg = f"Record with uid '{uid}' already exists"
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
            uid: The identifier the record is stored under.

        Raises:
            FileNotFoundError: If neither storage holds a record under `uid`.

        """
        found = False
        for storage in (self._hot, self._cold):
            if storage.exists(uid):
                storage.remove(uid)
                found = True
        if not found:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg)

    def exists(self, uid: str) -> bool:
        return self._hot.exists(uid) or self._cold.exists(uid)

    def size(self, uid: str) -> int:
        """Return the size in bytes of a record, asking the hot storage whenever it can answer.

        Args:
            uid: The identifier the record is stored under.

        Returns:
            The size of the record as the storage that answered holds it.

        Raises:
            FileNotFoundError: If neither storage holds a record under `uid`.

        """
        if self._hot.exists(uid):
            return self._hot.size(uid)
        return self._cold.size(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """Walk the cold storage, the only one that knows every record.

        Args:
            prefix: The prefix the yielded uids are filtered by, or `None` to yield them all.

        Yields:
            The uid of every record in the cold storage.

        """
        return self._cold.index(prefix)
