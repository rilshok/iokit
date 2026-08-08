__all__ = [
    "LocalStorage",
    "MemoryStorage",
    "StateStorage",
]

from collections.abc import Iterator
from pathlib import Path, PurePath
from typing import Any, TypeVar, overload

from iokit.codec.base import best_codec
from iokit.state import Enc, FormatState, Gzip, LoadedState, State

from .storage import Storage

S = TypeVar("S", bound=FormatState[Any])


class LocalStorage(Storage[bytes]):
    def __init__(self, root: Path | str) -> None:
        super().__init__()
        self._root = Path(root).resolve()

    def _path(self, uid: str) -> Path:
        """Return the path holding the record, checked to stay under the storage root."""
        path = (self._root / uid).resolve()
        if not path.is_relative_to(self._root):
            msg = f"Record with uid '{uid}' would land outside of the storage root"
            raise ValueError(msg)
        return path

    def pull(self, uid: str) -> bytes:
        path = self._path(uid)
        if not path.is_file():
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg)
        return path.read_bytes()

    def push(self, uid: str, record: bytes, *, force: bool = False) -> None:
        path = self._path(uid)
        if path.exists() and not force:
            msg = f"Record with uid '{uid}' already exists"
            raise FileExistsError(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(record)

    def remove(self, uid: str) -> None:
        path = self._path(uid)
        if not path.is_file():
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg)
        path.unlink()

    def exists(self, uid: str) -> bool:
        return self._path(uid).is_file()

    def size(self, uid: str) -> int:
        path = self._path(uid)
        if not path.is_file():
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg)
        return path.stat().st_size

    def index(self, prefix: str | None = None) -> Iterator[str]:
        for path in self._root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(self._root)
            # nothing hidden is a record, however deep it lies
            if any(part.startswith(".") for part in relative.parts):
                continue
            uid = relative.as_posix()
            if prefix is None or uid.startswith(prefix):
                yield uid


class MemoryStorage(Storage[bytes]):
    def __init__(self) -> None:
        super().__init__()
        self._records: dict[str, bytes] = {}

    def pull(self, uid: str) -> bytes:
        try:
            return self._records[uid]
        except KeyError as exc:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg) from exc

    def push(self, uid: str, record: bytes, *, force: bool = False) -> None:
        if uid in self._records and not force:
            msg = f"Record with uid '{uid}' already exists"
            raise FileExistsError(msg)
        self._records[uid] = record

    def remove(self, uid: str) -> None:
        if uid not in self._records:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg)
        del self._records[uid]

    def exists(self, uid: str) -> bool:
        return uid in self._records

    def size(self, uid: str) -> int:
        try:
            return len(self._records[uid])
        except KeyError as exc:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg) from exc

    def index(self, prefix: str | None = None) -> Iterator[str]:
        # a snapshot, so that pushing or removing while walking the index is not an error
        for uid in list(self._records):
            if prefix is None or uid.startswith(prefix):
                yield uid


class StateStorage(Storage[Any]):
    """Objects kept as states in a byte backend, the format taken from the uid extension.

    A uid such as `report.json` picks the codec, so the storage itself only adds the layers
    it is configured with: `.gz` for compression and `.enc` for password protection, in that
    order. The layers are part of the path the backend sees, never of the uid, and a storage
    reads back only what a storage configured the same way has written.
    """

    def __init__(
        self,
        backend: Storage[bytes],
        *,
        compression: int | bool | None = None,
        password: str | None = None,
        salt: str = "",
    ) -> None:
        super().__init__()
        self._backend = backend
        # `False` asks for no compression at all, where `0` is the gzip level that only stores
        self._compression = None if compression is False else compression
        self._password = password
        self._salt = salt

    def _path(self, uid: str) -> str:
        """Return the path the backend holds the record pushed under `uid` at."""
        if self._compression is not None:
            uid += Gzip.extension()
        if self._password is not None:
            uid += Enc.extension()
        return uid

    def _uid(self, path: str) -> str:
        """Return the uid of the record the backend holds at `path`."""
        if self._password is not None:
            path = path.removesuffix(Enc.extension())
        if self._compression is not None:
            path = path.removesuffix(Gzip.extension())
        return path

    @overload
    def pull_state(self, uid: str, expected_type: type[S]) -> S: ...

    @overload
    def pull_state(self, uid: str, expected_type: None = None) -> State[Any]: ...

    def pull_state(self, uid: str, expected_type: type[S] | None = None) -> S | State[Any]:
        """Read a record back as the state it was pushed as, pathed by its `uid`.

        Args:
            uid: The identifier the record was pushed under, extension included.
            expected_type: The format the state is asserted to be, or `None` to skip the check.

        Returns:
            The state stripped of the compression and encryption layers, pathed by `uid`.

        Raises:
            FileNotFoundError: If no record is stored under `uid`.

        """
        path = self._path(uid)
        try:
            data = self._backend.pull(path)
        except FileNotFoundError as exc:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg) from exc
        state: State[Any] = LoadedState(data, path=path)
        if self._password is not None:
            state = Enc.from_state(state).load(password=self._password, salt=self._salt)
        if self._compression is not None:
            state = Gzip.from_state(state).load()
        if expected_type is None:
            return state
        return expected_type.from_state(state)

    def pull(self, uid: str) -> object:
        return self.pull_state(uid).load()

    def push(self, uid: str, record: object, *, force: bool = False) -> None:
        with best_codec(PurePath(uid).name).encode(record) as content:
            state: State[Any] = LoadedState(content.read(), path=uid)
        if self._compression is not None:
            state = state.gzip(compression=int(self._compression))
        if self._password is not None:
            state = state.encrypt(password=self._password, salt=self._salt)
        try:
            self._backend.push(uid=state.path, record=state.data, force=force)
        except FileExistsError as exc:
            msg = f"Record with uid '{uid}' already exists"
            raise FileExistsError(msg) from exc

    def remove(self, uid: str) -> None:
        try:
            self._backend.remove(self._path(uid))
        except FileNotFoundError as exc:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg) from exc

    def exists(self, uid: str) -> bool:
        return self._backend.exists(self._path(uid))

    def size(self, uid: str) -> int:
        try:
            return self._backend.size(self._path(uid))
        except FileNotFoundError as exc:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg) from exc

    def index(self, prefix: str | None = None) -> Iterator[str]:
        for path in self._backend.index(prefix=prefix):
            yield self._uid(path)
