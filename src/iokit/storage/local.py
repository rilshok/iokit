__all__ = [
    "LocalStorage",
    "MemoryStorage",
    "StateStorage",
    "load_file",
    "save_file",
    "save_temp",
]

import tempfile
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

from iokit import State, auto_state, supported_extensions
from iokit.tools.time import fromtimestamp

from .storage import BackendStorage, Storage

PathLike = str | Path


def load_file(path: PathLike, /) -> State:
    path = Path(path).resolve()
    mtime = fromtimestamp(path.stat().st_mtime)
    return State(path.read_bytes(), name=path.name, time=mtime).cast()


def save_file(
    state: State,
    /,
    root: PathLike = "",
    *,
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
def save_temp(state: State, /) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield save_file(state, root=temp_dir)


class LocalStorage(BackendStorage):
    def __init__(self, root: Path | str) -> None:
        super().__init__()
        self._root = Path(root).resolve()

    def pull(self, uid: str) -> bytes:
        return load_file(self._root / uid).data

    def push(self, uid: str, record: bytes, *, force: bool = False) -> None:
        try:
            save_file(State(record, name=uid), root=self._root, force=force)
        except FileExistsError as exc:
            msg = f"Record with uid '{uid}' already exists"
            raise FileExistsError(msg) from exc

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


class MemoryStorage(BackendStorage):
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

    def index(self, prefix: str | None = None) -> Iterator[str]:
        for uid in self._records:
            if prefix is None or uid.startswith(prefix):
                yield uid


class StateStorage(Storage[Any]):
    def __init__(  # noqa: PLR0913
        self,
        backend: BackendStorage,
        *,
        compression: int | bool | None = None,
        password: str | None = None,
        waveform_to: Literal["wav", "flac", "mp3", "ogg"] = "wav",
        dataframe_to: Literal["csv", "tsv"] = "csv",
        builtin_to: Literal["json", "yaml"] = "json",
    ) -> None:
        super().__init__()
        self._backend = backend
        self._extensions = supported_extensions()

        self._compression = compression
        self._password = password
        self._waveform_to = waveform_to
        self._dataframe_to = dataframe_to
        self._builtin_to = builtin_to

    def _remove_extension(self, name: str) -> str:
        while True:
            for ext in self._extensions:
                suffix = f".{ext}"
                if name.endswith(suffix):
                    name = name.removesuffix(suffix)
                    break
            else:
                break
        return name

    def _name(self, uid: str) -> str:
        for name in self._backend.index(prefix=uid):
            if self._remove_extension(name) == uid:
                return name
        msg = f"Record with uid '{uid}' does not exist"
        raise FileNotFoundError(msg)

    def pull_state(self, uid: str) -> State:
        name = self._name(uid)
        try:
            data = self._backend.pull(name)
            return State(data, name=name).cast()
        except FileNotFoundError as exc:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg) from exc

    def pull(self, uid: str) -> object:
        state = self.pull_state(uid)
        if self._password is not None:
            state = state.load().load(password=self._password)
        if self._compression is not None:
            state = state.load()
        return state.load()

    def push(self, uid: str, record: object, *, force: bool = False) -> None:
        state = auto_state(
            record,
            name=uid,
            compression=self._compression,
            password=self._password,
            waveform_to=self._waveform_to,
            dataframe_to=self._dataframe_to,
            builtin_to=self._builtin_to,
        )
        try:
            return self._backend.push(uid=str(state.name), record=state.data, force=force)
        except FileExistsError as exc:
            msg = f"Record with uid '{uid}' already exists"
            raise FileExistsError(msg) from exc

    def remove(self, uid: str) -> None:
        try:
            return self._backend.remove(self._name(uid))
        except FileNotFoundError as exc:
            msg = f"Record with uid '{uid}' does not exist"
            raise FileNotFoundError(msg) from exc

    def exists(self, uid: str) -> bool:
        return self._backend.exists(self._name(uid))

    def index(self, prefix: str | None = None) -> Iterator[str]:
        for idx in self._backend.index(prefix=prefix):
            yield self._remove_extension(idx)
