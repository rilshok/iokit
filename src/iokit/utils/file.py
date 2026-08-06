__all__ = ["file"]

from pathlib import Path
from typing import Any, TypeVar, overload

from iokit.state import FileState, FormatState

F = TypeVar("F", bound=FormatState[Any])

PathLike = str | Path


@overload
def file(path: PathLike, expected_type: type[F]) -> F: ...


@overload
def file(path: PathLike, expected_type: None = None) -> FileState[Any]: ...


def file(path: PathLike, expected_type: type[F] | None = None) -> F | FileState[Any]:
    """Take a file on disk as a state, read from it as it is asked for.

    Args:
        path: The file to stand for.
        expected_type: The format the file is expected to be in, its extension checked
            against the path. Left out, the state stays untyped.

    Returns:
        The state of the file, timestamped after its modification time.

    Raises:
        FileNotFoundError: If `path` leads to no regular file.
        ValueError: If `path` lacks the extension of `expected_type`.
    """
    state: FileState[Any] = FileState(path)
    if expected_type is None:
        return state
    return expected_type.from_state(state)
