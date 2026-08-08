__all__ = [
    "CountingStorage",
]

from collections import Counter
from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import TypeVar

from .storage import Storage

T = TypeVar("T")


class CountingStorage(Storage[T]):
    """Any storage, wrapped to keep a tally of the operations asked of it.

    Every call is counted under the name of the operation, whether it succeeds or raises,
    and the tally is readable through `calls`. What `index` counts is the call itself, not
    the records it goes on to yield, since the walk happens as the caller consumes it.

    The wrapper is meant for tests and for measuring the traffic a storage sees, so it holds
    nothing of its own and passes records through untouched. Counting is not thread safe.
    """

    def __init__(self, backend: Storage[T]) -> None:
        super().__init__()
        self._backend = backend
        self._calls: Counter[str] = Counter()

    @property
    def calls(self) -> Mapping[str, int]:
        """A live read-only view of how many times each operation has been called so far.

        Operations never called are absent, rather than present as a zero.
        """
        return MappingProxyType(self._calls)

    @property
    def backend(self) -> Storage[T]:
        """The storage the calls are counted for and passed to."""
        return self._backend

    def reset(self) -> None:
        """Forget the tally, leaving the storage itself alone."""
        self._calls.clear()

    def pull(self, uid: str) -> T:
        self._calls["pull"] += 1
        return self._backend.pull(uid)

    def push(self, uid: str, record: T, *, force: bool = False) -> None:
        self._calls["push"] += 1
        self._backend.push(uid, record, force=force)

    def remove(self, uid: str) -> None:
        self._calls["remove"] += 1
        self._backend.remove(uid)

    def exists(self, uid: str) -> bool:
        self._calls["exists"] += 1
        return self._backend.exists(uid)

    def size(self, uid: str) -> int:
        self._calls["size"] += 1
        return self._backend.size(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        self._calls["index"] += 1
        return self._backend.index(prefix)
