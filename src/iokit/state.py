__all__ = [
    "State",
    "filter_states",
    "find_state",
]

from collections.abc import Generator, Iterable, Iterator
from contextlib import suppress
from datetime import datetime
from fnmatch import fnmatch
from io import BytesIO

from humanize import naturalsize
from typing_extensions import Self

from iokit.tools.time import now

from .checksum import ChecksumMixin


class StateName:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def stem(self) -> str:
        split = self._name.split(sep=".", maxsplit=1)
        return split[0]

    @stem.setter
    def stem(self, new: str) -> None:
        suffix = ".".join(self.suffixes)
        self._name = f"{new}.{suffix}"

    @property
    def suffix(self) -> str:
        split = self._name.rsplit(sep=".", maxsplit=1)
        if len(split) == 2:  # noqa: PLR2004
            return f"{split[-1]}"
        msg = f"State name '{self._name}' does not have a suffix"
        raise ValueError(msg)

    @property
    def suffixes(self) -> tuple[str, ...]:
        split = self._name.split(sep=".")[1:]
        return tuple(f"{s}" for s in split)

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return self._name

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self._name == other
        if isinstance(other, StateName):
            return self._name == other._name
        msg = f"Expected str or StateName, got {type(other).__name__}"
        raise NotImplementedError(msg)

    @classmethod
    def make(cls, stem: "str | StateName", suffix: str) -> Self:
        if suffix:
            return cls(f"{stem}.{suffix}")
        return cls(str(stem))


class State(ChecksumMixin):
    _suffix: str = ""
    _suffixes: tuple[str, ...] = ("",)

    def __init__(
        self,
        data: bytes,
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        self._data = data
        self._name = StateName.make(name, self._suffix)
        self._time = time or now()

    def __init_subclass__(
        cls,
        suffix: str | None = None,
        suffixes: tuple[str, ...] | None = None,
    ) -> None:
        if suffix is None and suffixes is not None:
            if len(suffixes) == 0:
                msg = "State subclasses must define at least one suffix"
                raise ValueError(msg)
            suffix = suffixes[0]
        if suffix is not None and suffixes is None:
            suffixes = (suffix,)

        if suffix is not None and suffixes is not None and suffix not in suffixes:
            suffixes = (suffix, *suffixes)

        if suffix is None or suffixes is None:
            msg = "State subclasses must define a suffix or suffixes"
            raise ValueError(msg)

        cls._suffix = suffix
        cls._suffixes = suffixes

    @classmethod
    def suffix(cls) -> str:
        return cls._suffix

    @property
    def name(self) -> StateName:
        return self._name

    @name.setter
    def name(self, value: str | StateName) -> None:
        if isinstance(value, str):
            value = StateName(value)
        self._name = value

    @property
    def time(self) -> datetime:
        return self._time

    @time.setter
    def time(self, value: datetime) -> None:
        self._time = value

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def buffer(self) -> BytesIO:
        return BytesIO(self._data)

    @property
    def size(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        size = naturalsize(self.size, gnu=True)
        return f"{self.name} ({size})"

    @classmethod
    def _by_suffix(cls, suffix: str) -> type[Self]:
        if suffix.lower() in cls._suffixes:
            return cls
        for kls in cls.__subclasses__():
            with suppress(ValueError):
                return kls._by_suffix(suffix)  # noqa: SLF001
        msg = f"Unknown state suffix '{suffix}'"
        raise ValueError(msg)

    def cast(self) -> "State":
        with suppress(ValueError):
            klass = self._by_suffix(self.name.suffix)
            state = klass.__new__(klass)
            state._data = self.data  # noqa: SLF001
            state._name = self.name  # noqa: SLF001
            state._time = self.time  # noqa: SLF001
            return state
        return self

    def load(self) -> object:
        if not self.name.suffix:
            return self.data
        state = self.cast()
        if type(state) is State:  # pylint: disable=unidiomatic-typecheck
            msg = f"Cannot load state with suffix '{self.name.suffix}'"
            raise NotImplementedError(msg)
        return state.load()


def _sub_extensions(kls: type[State]) -> Iterator[str]:
    for k in kls.__subclasses__():
        if suffix := k.suffix():
            yield suffix
        yield from _sub_extensions(k)


def supported_extensions() -> list[str]:
    return list(_sub_extensions(State))


def filter_states(states: Iterable[State], pattern: str) -> Generator[State, None, None]:
    for state in states:
        if fnmatch(str(state.name), pattern):
            yield state


def find_state(states: Iterable[State], pattern: str) -> State:
    for state in filter_states(states, pattern):
        return state
    msg = f"State not found: {pattern!r}"
    raise FileNotFoundError(msg)
