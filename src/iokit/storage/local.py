__all__ = [
    "load_file",
    "save_file",
    "save_temp",
]
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from iokit.state import State
from iokit.tools.time import fromtimestamp

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
    path.write_bytes(state.data.getvalue())
    return path


@contextmanager
def save_temp(state: State) -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir:
        yield save_file(state, root=temp_dir)
