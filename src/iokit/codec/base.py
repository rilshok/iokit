import importlib.metadata as md
from collections.abc import Iterable
from dataclasses import dataclass, replace
from fnmatch import fnmatch
from importlib import import_module
from typing import Any, BinaryIO, Generic, TypeVar

from packaging.requirements import Requirement

T = TypeVar("T", bound=object)


class Codec(Generic[T]):
    keys: str | Iterable[str]

    def encode(self, data: T) -> BinaryIO:
        raise NotImplementedError

    def decode(self, buffer: BinaryIO) -> T:
        raise NotImplementedError


class Pattern(str):
    def __len__(self) -> int:
        return len(self.replace("*", ""))

    def __call__(self, string: str) -> bool:
        return fnmatch(name=string, pat=str(self))


def _satisfies(req: Requirement) -> bool:
    try:
        version = md.version(req.name)
    except md.PackageNotFoundError:
        return False
    return req.specifier.contains(version, prereleases=True)


def _hashable(value: object) -> bool:
    try:
        hash(value)
    except TypeError:
        return False
    return True


_CODEC_CACHE: dict[int, Codec[Any]] = {}


@dataclass
class CodecSpec:
    module: str
    attriute: str
    config: dict[str, Any]
    requirements: list[Requirement]

    def __post_init__(self) -> None:
        unhashable = [name for name, value in self.config.items() if not _hashable(value)]
        if unhashable:
            names = ", ".join(f"{name}={self.config[name]!r}" for name in sorted(unhashable))
            msg = f"Codec config values must be hashable, got unhashable: {names}"
            raise TypeError(msg)

        self.config = {name: self.config[name] for name in sorted(self.config)}
        self.requirements = sorted(self.requirements, key=str)

    def __hash__(self) -> int:
        state = (
            self.module,
            self.attriute,
            tuple((k, hash(v)) for k, v in self.config.items()),
            tuple(str(r) for r in self.requirements),
        )
        return hash(state)

    def produce(self, **config: object) -> Codec[Any]:
        merged = self.config | config
        obj = replace(self, config={key: merged[key] for key in self.config}) if config else self

        if codec := _CODEC_CACHE.get(hash(obj)):
            return codec

        requirements = [r for r in obj.requirements if not _satisfies(r)]
        if requirements:
            req_str = ", ".join(str(r) for r in requirements)
            install_cmd = "pip install " + " ".join(r.name for r in requirements)
            msg = f"Missing required packages: {req_str}. Install with: {install_cmd}"
            raise ModuleNotFoundError(msg)

        module = import_module(obj.module)
        kls = getattr(module, obj.attriute)
        if not issubclass(kls, Codec):
            msg = ""
            raise TypeError(msg)
        codec = kls(**obj.config)
        _CODEC_CACHE[hash(obj)] = codec
        return codec


_CODEC_REGISTRY: dict[Pattern, CodecSpec] = {}


def registrate(
    pattern: str,
    spec: str,
    requirements: Iterable[str] | None = None,
    *,
    override: bool = False,
    **kwargs: object,
) -> None:
    requirements = set(requirements or ())
    if pattern.lower() != pattern:
        msg = ""
        raise ValueError(msg)
    module, _, attr = spec.partition(":")
    if not module or not attr:
        msg = ""
        raise ValueError(msg)
    if not override and pattern in _CODEC_REGISTRY:
        msg = ""
        raise ValueError(msg)
    _CODEC_REGISTRY[Pattern(pattern)] = CodecSpec(
        module=module,
        attriute=attr,
        config=kwargs,
        requirements=[Requirement(r) for r in requirements],
    )


def best_codec(name: str, **config: object) -> Codec[Any]:
    name = name.lower()
    pattern = max((pattern for pattern in _CODEC_REGISTRY if pattern(name)), key=Pattern.__len__)
    return _CODEC_REGISTRY[pattern].produce(**config)


registrate("*", "iokit.codec.bin:BinCodec")
registrate("*.bin", "iokit.codec.bin:BinCodec")
registrate("*.dat", "iokit.codec.bin:BinCodec")
registrate(
    "*.json",
    "iokit.codec.json:JsonCodec",
    compact=False,
    ensure_ascii=False,
    allow_nan=False,
)

registrate("*.zip", "iokit.codec.zip:ZipCodec", buffered=False)
