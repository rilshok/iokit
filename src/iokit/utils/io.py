__all__ = [
    "load_file",
    "save_file",
    "save_temp",
]

import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import TypeVar, overload

from iokit.utils.state import State
from iokit.utils.time import fromtimestamp

PathLike = str | Path

S = TypeVar("S", bound=State)


@overload
def load_file(path: PathLike, expected_type: type[S]) -> S: ...


@overload
def load_file(path: PathLike, expected_type: None = None) -> State: ...


def load_file(path: PathLike, expected_type: type[S] | None = None) -> S | State:
    path = Path(path).resolve()
    mtime = fromtimestamp(path.stat().st_mtime)
    return State(path.read_bytes(), name=path.name, time=mtime).cast(expected_type)


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
def save_temp(state: State | bytes | BytesIO, /) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        if isinstance(state, State):
            yield save_file(state, root=temp_dir)
            return
        if isinstance(state, BytesIO):
            state = state.getvalue()
        path = Path(temp_dir) / "data"
        path.write_bytes(state)
        yield path
