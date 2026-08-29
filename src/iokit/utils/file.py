"""Lazy-load files into state objects with automatic format detection."""

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
    """Load a file as a lazy state with automatic format detection.

    Args:
        path: Path to the file.
        expected_type: Expected format type; extension verified against `path`.

    Returns:
        The file state, timestamped.

    Raises:
        FileNotFoundError: If `path` is not a file.
        ValueError: If `path` lacks extension of `expected_type`.

    """
    state: FileState[Any] = FileState(path)
    if expected_type is None:
        return state
    return expected_type.from_state(state)
