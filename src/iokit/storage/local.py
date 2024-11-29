__all__ = [
    "load_file",
    "save_file",
    "save_temp",
    "LocalStorage",
    "LocalStorageFactory",
    "StateStorage",
]
import tempfile
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from iokit import State
from iokit.tools.time import fromtimestamp

from .storage import Storage, StorageFactory

PathLike = str | Path


def load_file(path: PathLike) -> State:
    path = Path(path).resolve()
    mtime = fromtimestamp(path.stat().st_mtime)
    return State(data=path.read_bytes(), name=path.name, time=mtime).cast()


def save_file(
    state: State,
    root: PathLike = "",
    parents: bool = False,
    force: bool = False,
) -> Path:
    root = Path(root).resolve()
    path = (root / str(state.name)).resolve()
    if not path.is_relative_to(root):
        msg = f"Path is outside of root: root='{root!s}', state.name='{state.name!s}'"
        raise ValueError(msg)
    if path.exists() and not force:
        msg = f"File already exists: path='{path!s}'"
        raise FileExistsError(msg)
    root.mkdir(parents=parents, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(state.data)
    return path


@contextmanager
def save_temp(state: State) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield save_file(state, root=temp_dir)


class LocalStorage(Storage[bytes]):
    def __init__(self, root: Path | str):
        super().__init__()
        root = Path(root).resolve()
        root.mkdir(parents=False, exist_ok=True)
        self._root = root

    def pull(self, uid: str) -> bytes:
        return Path(self._root / uid).read_bytes()

    def push(self, uid: str, record: bytes, *, force: bool = False) -> None:
        path = Path(self._root / uid)
        if path.exists() and not force:
            msg = f"Record with uid '{uid}' already exists"
            raise FileExistsError(msg)
        path.write_bytes(record)

    def remove(self, uid: str) -> None:
        path = Path(self._root / uid)
        if not path.exists():
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg)
        path.unlink()

    def exists(self, uid: str) -> bool:
        return Path(self._root / uid).exists()

    def index(self, prefix: str | None = None) -> Iterator[str]:
        pattern = "*" if prefix is None else f"{prefix}*"
        for p in self._root.rglob(pattern):
            uid = str(p.relative_to(self._root))
            if uid.startswith("."):
                continue
            yield uid


class LocalStorageFactory(StorageFactory):
    def __init__(self, root: Path | str):
        super().__init__()
        root = Path(root).resolve()
        if not root.exists():
            root.mkdir(parents=False, exist_ok=True)
        self._root = root

    def create(self, name: str) -> Storage[bytes]:
        root = (self._root / name).resolve()
        if not root.is_relative_to(self._root):
            msg = (
                f"Storage name '{name}' is incorrect"
                f"because its use would result in a path outside the root '{self._root}'"
            )
            raise ValueError(msg)
        root.mkdir(parents=True, exist_ok=True)
        return LocalStorage(root=root)


S = TypeVar("S", bound=State)


class StateStorage(Storage[S]):
    def __init__(self, backend: Storage[bytes], scheme: type[S]):
        super().__init__()
        self._backend = backend
        self._scheme = scheme
        self._suffix = f".{scheme.suffix()}"

    def _cast_state(self, state: State) -> S:
        state = state.cast()
        if not isinstance(state, self._scheme):
            msg = (
                f"Expected state to be an instance of '{self._scheme.__name__}'"
                f" but got an instance of '{type(state).__name__}'"
            )
            raise TypeError(msg)
        return state

    def _name(self, uid: str) -> str:
        return f"{uid}{self._suffix}"

    def pull(self, uid: str) -> S:
        name = self._name(uid)
        data = self._backend.pull(name)
        state = State(data=data, name=name)
        state = self._cast_state(state)
        return state

    def push(self, uid: str, record: S, *, force: bool = False) -> None:
        return self._backend.push(
            uid=self._name(uid),
            record=self._cast_state(record).data,
            force=force,
        )

    def remove(self, uid: str) -> None:
        return self._backend.remove(self._name(uid))

    def exists(self, uid: str) -> bool:
        return self._backend.exists(self._name(uid))

    def index(self, prefix: str | None = None) -> Iterator[str]:
        for idx in self._backend.index(prefix=prefix):
            yield idx.removesuffix(self._suffix)


class MemoryStorage(Storage[bytes]):
    def __init__(self):
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

    def index(self, prefix: str | None = None) -> Iterator[str]:
        for uid in self._records:
            if prefix is None or uid.startswith(prefix):
                yield uid


class MemoryStorageFactory(StorageFactory):
    def create(self, name: str) -> Storage[bytes]:
        return MemoryStorage()
