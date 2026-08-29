"""Storage wrapper that counts operations for testing and monitoring."""

__all__ = [
    "CountingStorage",
]

from collections import Counter
from collections.abc import Iterator
from typing import TypeVar

from .storage import Storage

T = TypeVar("T")


class CountingStorage(Storage[T]):
    """Any storage, wrapped to keep a tally of the operations asked of it.

    Every call is counted under the name of the operation, whether it succeeds or raises,
    and the tally is readable through `calls`, which hands back a snapshot of the counts as
    they stand at that moment. What `index` counts is the call itself, not
    the records it goes on to yield, since the walk happens as the caller consumes it.

    The wrapper is meant for tests and for measuring the traffic a storage sees, so it holds
    nothing of its own and passes records through untouched. Counting is not thread safe.
    """

    def __init__(self, backend: Storage[T]) -> None:
        """Initialize a counting wrapper around a storage backend.

        Args:
            backend: The storage backend to wrap and count operations for.

        """
        super().__init__()
        self._backend = backend
        self._calls: Counter[str] = Counter()

    @property
    def calls(self) -> dict[str, int]:
        """A snapshot of how many times each operation has been called so far.

        The snapshot is the caller's own to keep or change, later calls not reaching back
        into it. Operations never called are absent, rather than present as a zero.
        """
        return dict(self._calls)

    @property
    def backend(self) -> Storage[T]:
        """The storage the calls are counted for and passed to."""
        return self._backend

    def reset(self) -> None:
        """Forget the tally, leaving the storage itself alone."""
        self._calls.clear()

    def pull(self, uid: str) -> T:
        """Retrieve a record, counting the operation.

        Args:
            uid: The unique identifier of the record.

        Returns:
            The requested record.

        """
        self._calls["pull"] += 1
        return self._backend.pull(uid)

    def push(self, uid: str, record: T, *, force: bool = False) -> None:
        """Store a record, counting the operation.

        Args:
            uid: The unique identifier for the record.
            record: The record to store.
            force: Whether to overwrite an existing record.

        """
        self._calls["push"] += 1
        self._backend.push(uid, record, force=force)

    def remove(self, uid: str) -> None:
        """Delete a record, counting the operation.

        Args:
            uid: The unique identifier of the record to remove.

        """
        self._calls["remove"] += 1
        self._backend.remove(uid)

    def exists(self, uid: str) -> bool:
        """Check if a record exists, counting the operation.

        Args:
            uid: The unique identifier to check.

        Returns:
            Whether a record with the given uid exists.

        """
        self._calls["exists"] += 1
        return self._backend.exists(uid)

    def size(self, uid: str) -> int:
        """Get the size of a record, counting the operation.

        Args:
            uid: The unique identifier of the record.

        Returns:
            The size of the record in bytes.

        """
        self._calls["size"] += 1
        return self._backend.size(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """List all records, counting the operation.

        Args:
            prefix: Optional prefix to filter records.

        Yields:
            The unique identifiers of matching records.

        """
        self._calls["index"] += 1
        return self._backend.index(prefix)
