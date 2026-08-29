"""Local and in-memory storage implementations."""

__all__ = [
    "LocalStorage",
    "MemoryStorage",
    "StateStorage",
    "StreamLocalStorage",
    "StreamMemoryStorage",
]

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path, PurePath
from shutil import copyfileobj
from typing import Any, BinaryIO, TypeVar, overload

from iokit.codec.base import best_codec
from iokit.state import Enc, FormatState, Gzip, LoadedState, State

from .storage import BinaryStorage, Storage, is_record_uid, validate_uid

S = TypeVar("S", bound=FormatState[Any])


class StreamLocalStorage(Storage[BinaryIO]):
    """Local filesystem storage for records as files."""

    def __init__(self, root: Path | str) -> None:
        """Initialize filesystem storage at `root`.

        Args:
            root: Root directory for records.

        """
        super().__init__()
        self._root = Path(root).resolve()

    def _path(self, uid: str) -> Path:
        """Resolve `uid` to a path under root, validated.

        Args:
            uid: Record identifier as relative POSIX path.

        Returns:
            Resolved file path.

        Raises:
            ValueError: If `uid` is invalid or outside root.

        """
        path = self._root.joinpath(*validate_uid(uid)).resolve()
        if not path.is_relative_to(self._root):
            msg = f"Record with uid {uid!r} would land outside of the storage root"
            raise ValueError(msg)
        return path

    def pull(self, uid: str) -> BinaryIO:
        """Open a record file for reading.

        Args:
            uid: Record identifier.

        Returns:
            Open file in read mode.

        Raises:
            FileNotFoundError: If record does not exist.

        """
        path = self._path(uid)
        if not path.is_file():
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg)
        return path.open("rb")

    def size(self, uid: str) -> int:
        """Get record file size in bytes.

        Args:
            uid: Record identifier.

        Returns:
            File size in bytes.

        Raises:
            FileNotFoundError: If record does not exist.

        """
        path = self._path(uid)
        if not path.is_file():
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg)
        return path.stat().st_size

    def push(self, uid: str, record: BinaryIO, *, force: bool = False) -> None:
        """Write a record file.

        Args:
            uid: Record identifier.
            record: Binary stream to write.
            force: Overwrite existing.

        Raises:
            FileExistsError: If exists and `force` is not set.

        """
        path = self._path(uid)
        if path.exists() and not force:
            msg = f"Record with uid {uid!r} already exists"
            raise FileExistsError(msg)
        path.parent.mkdir(parents=True, exist_ok=True)
        with record, path.open("wb") as file:
            copyfileobj(record, file)

    def remove(self, uid: str) -> None:
        """Delete a record file.

        Args:
            uid: Record identifier.

        Raises:
            FileNotFoundError: If does not exist.

        """
        path = self._path(uid)
        if not path.is_file():
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg)
        path.unlink()

    def exists(self, uid: str) -> bool:
        """Check if a record file exists.

        Args:
            uid: Record identifier.

        Returns:
            True if exists.

        """
        return self._path(uid).is_file()

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """Yield record files, optionally filtered by prefix.

        Args:
            prefix: Filter by prefix, or `None` for all.

        Yields:
            Record identifiers.

        """
        for path in self._root.rglob("*"):
            if not path.is_file():
                continue
            uid = path.relative_to(self._root).as_posix()
            if prefix is None or uid.startswith(prefix):
                yield uid


class LocalStorage(BinaryStorage):
    """Local filesystem storage for binary records."""

    def __init__(self, root: Path | str) -> None:
        """Initialize filesystem storage at `root`.

        Args:
            root: Root directory for records.

        """
        super().__init__(StreamLocalStorage(root))


class MemoryStorage(Storage[bytes]):
    """In-memory storage of bytes in a dictionary."""

    def __init__(self, records: dict[str, bytes] | None = None) -> None:
        """Initialize with optional `records` dict.

        Args:
            records: Dictionary to adopt; new one created if `None`.

        """
        super().__init__()
        # the mapping is adopted, not copied, so writes on either side are seen by the other
        self._records: dict[str, bytes] = records if records is not None else {}

    @property
    def records(self) -> dict[str, bytes]:
        """The mapping of uid to record the storage reads and writes."""
        return self._records

    def pull(self, uid: str) -> bytes:
        """Retrieve a record from the in-memory dictionary.

        Args:
            uid: The unique identifier of the record.

        Returns:
            The record data as bytes.

        Raises:
            FileNotFoundError: If the record does not exist.

        """
        validate_uid(uid)
        try:
            return self._records[uid]
        except KeyError as exc:
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg) from exc

    def push(self, uid: str, record: bytes, *, force: bool = False) -> None:
        """Store a record in the in-memory dictionary.

        Args:
            uid: The unique identifier for the record.
            record: The record data as bytes.
            force: Whether to overwrite an existing record.

        Raises:
            FileExistsError: If the record exists and force is False.

        """
        validate_uid(uid)
        if uid in self._records and not force:
            msg = f"Record with uid {uid!r} already exists"
            raise FileExistsError(msg)
        self._records[uid] = record

    def remove(self, uid: str) -> None:
        """Delete a record from the in-memory dictionary.

        Args:
            uid: The unique identifier of the record to remove.

        Raises:
            FileNotFoundError: If the record does not exist.

        """
        validate_uid(uid)
        if uid not in self._records:
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg)
        del self._records[uid]

    def exists(self, uid: str) -> bool:
        """Check if a record exists in the in-memory dictionary.

        Args:
            uid: The unique identifier to check.

        Returns:
            Whether a record with the given uid exists.

        """
        validate_uid(uid)
        return uid in self._records

    def size(self, uid: str) -> int:
        """Get the size of a record in the in-memory dictionary.

        Args:
            uid: The unique identifier of the record.

        Returns:
            The size of the record in bytes.

        Raises:
            FileNotFoundError: If the record does not exist.

        """
        validate_uid(uid)
        try:
            return len(self._records[uid])
        except KeyError as exc:
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg) from exc

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """List all valid records in the dictionary, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter records.

        Yields:
            The unique identifiers of matching records.

        """
        # a snapshot, so that pushing or removing while walking the index is not an error
        for uid in list(self._records):
            # a key put in the mapping by hand may be no uid at all, and names no record
            if not is_record_uid(uid):
                continue
            if prefix is None or uid.startswith(prefix):
                yield uid


class StreamMemoryStorage(Storage[BinaryIO]):
    """A stream view over records a `MemoryStorage` keeps in memory.

    Records live as bytes in the wrapped storage either way, so a pull hands out a reader over
    a snapshot of them and a push drains the stream into bytes before storing it.
    """

    def __init__(self, backend: MemoryStorage | None = None) -> None:
        """Initialize stream storage over in-memory records.

        Args:
            backend: A MemoryStorage instance; a new one is created if None.

        """
        super().__init__()
        self._backend = backend if backend is not None else MemoryStorage()

    def pull(self, uid: str) -> BinaryIO:
        """Retrieve a record as a binary stream.

        Args:
            uid: The unique identifier of the record.

        Returns:
            A BytesIO stream of the record data.

        """
        return BytesIO(self._backend.pull(uid))

    def push(self, uid: str, record: BinaryIO, *, force: bool = False) -> None:
        """Store a record from a binary stream.

        Args:
            uid: The unique identifier for the record.
            record: The binary I/O stream to read from.
            force: Whether to overwrite an existing record.

        Raises:
            FileExistsError: If the record exists and force is False.

        """
        if self._backend.exists(uid) and not force:
            msg = f"Record with uid {uid!r} already exists"
            raise FileExistsError(msg)
        with record:
            data = record.read()
        self._backend.push(uid, data, force=True)

    def remove(self, uid: str) -> None:
        """Delete a record from storage.

        Args:
            uid: The unique identifier of the record to remove.

        """
        self._backend.remove(uid)

    def exists(self, uid: str) -> bool:
        """Check if a record exists in storage.

        Args:
            uid: The unique identifier to check.

        Returns:
            Whether a record with the given uid exists.

        """
        return self._backend.exists(uid)

    def size(self, uid: str) -> int:
        """Get the size of a record in storage.

        Args:
            uid: The unique identifier of the record.

        Returns:
            The size of the record in bytes.

        """
        return self._backend.size(uid)

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """List all records in storage, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter records.

        Yields:
            The unique identifiers of matching records.

        """
        return self._backend.index(prefix=prefix)


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
        """Initialize state storage with optional compression and encryption.

        Args:
            backend: A byte storage backend for holding encoded records.
            compression: Gzip level (0-9), True for default, False for none, or None.
            password: Password for encryption; None disables encryption.
            salt: Extra input for key derivation.

        """
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
            msg = f"Record with uid {uid!r} does not exist"
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
        """Load a record, decoding it from the uid-specified format.

        Args:
            uid: The identifier of the record, whose extension specifies the codec.

        Returns:
            The decoded record.

        Raises:
            FileNotFoundError: If no record is stored under the uid.

        """
        return self.pull_state(uid).load()

    def push(self, uid: str, record: object, *, force: bool = False) -> None:
        """Store a record, encoding it with the codec specified by the uid extension.

        Args:
            uid: The identifier for the record, whose extension specifies the codec.
            record: The object to encode and store.
            force: Whether to overwrite an existing record.

        Raises:
            FileExistsError: If the record exists and force is False.

        """
        with best_codec(PurePath(uid).name).encode(record) as content:
            state: State[Any] = LoadedState(content.read(), path=uid)
        if self._compression is not None:
            state = state.gzip(compression=int(self._compression))
        if self._password is not None:
            state = state.encrypt(password=self._password, salt=self._salt)
        try:
            self._backend.push(uid=state.path, record=state.data, force=force)
        except FileExistsError as exc:
            msg = f"Record with uid {uid!r} already exists"
            raise FileExistsError(msg) from exc

    def remove(self, uid: str) -> None:
        """Delete a record from storage.

        Args:
            uid: The unique identifier of the record to remove.

        Raises:
            FileNotFoundError: If no record is stored under the uid.

        """
        try:
            self._backend.remove(self._path(uid))
        except FileNotFoundError as exc:
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg) from exc

    def exists(self, uid: str) -> bool:
        """Check if a record exists in storage.

        Args:
            uid: The unique identifier to check.

        Returns:
            Whether a record with the given uid exists.

        """
        return self._backend.exists(self._path(uid))

    def size(self, uid: str) -> int:
        """Get the size of a record in storage.

        Args:
            uid: The unique identifier of the record.

        Returns:
            The size of the record in bytes.

        Raises:
            FileNotFoundError: If no record is stored under the uid.

        """
        try:
            return self._backend.size(self._path(uid))
        except FileNotFoundError as exc:
            msg = f"Record with uid {uid!r} does not exist"
            raise FileNotFoundError(msg) from exc

    def index(self, prefix: str | None = None) -> Iterator[str]:
        """List all records in storage, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter records.

        Yields:
            The unique identifiers of matching records.

        """
        for path in self._backend.index(prefix=prefix):
            yield self._uid(path)
