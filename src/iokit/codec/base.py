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
    cacheble: bool

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
        if obj.cacheble:
            _CODEC_CACHE[hash(obj)] = codec
        return codec


_CODEC_REGISTRY: list[tuple[Pattern, CodecSpec]] = []


def registrate(
    pattern: str,
    spec: str,
    requirements: Iterable[str] | None = None,
    *,
    override: bool = False,
    cacheble: bool = True,
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
    entry = (
        Pattern(pattern),
        CodecSpec(
            module=module,
            attriute=attr,
            config=kwargs,
            requirements=[Requirement(r) for r in requirements],
            cacheble=cacheble,
        ),
    )
    if override:
        _CODEC_REGISTRY.insert(0, entry)
    else:
        _CODEC_REGISTRY.append(entry)


def _install_hint(spec: CodecSpec) -> str:
    missing = [r for r in spec.requirements if not _satisfies(r)]
    codec = f"{spec.module}:{spec.attriute}"
    if not missing:
        return f"{codec} (module {spec.module!r} is not importable)"
    packages = " ".join(sorted({r.name for r in missing}))
    return f"{codec}: pip install {packages}"


def best_codec(name: str, **config: object) -> Codec[Any]:
    name = name.lower()
    matched = [(pattern, spec) for pattern, spec in _CODEC_REGISTRY if pattern(name)]
    if not matched:
        msg = f"No codec registered for {name!r}"
        raise LookupError(msg)

    score = max(len(pattern) for pattern, _ in matched)
    candidates = [spec for pattern, spec in matched if len(pattern) == score]

    failures: list[tuple[CodecSpec, ModuleNotFoundError]] = []
    for spec in candidates:
        try:
            return spec.produce(**config)
        except ModuleNotFoundError as exc:  # noqa: PERF203
            failures.append((spec, exc))

    if len(failures) == 1:
        raise failures[0][1]

    options = "; ".join(_install_hint(spec) for spec, _ in failures)
    msg = (
        f"No codec for {name!r} could be created, all {len(failures)} candidates are missing "
        f"their dependencies. Install one of the following option groups: {options}"
    )
    raise ModuleNotFoundError(msg) from failures[-1][1]


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
registrate("*.yaml", "iokit.codec.yaml:YamlCodec")
registrate("*.yml", "iokit.codec.yaml:YamlCodec")
registrate("*.txt", "iokit.codec.text:TextCodec", encoding="utf-8")
registrate("*.enc", "iokit.codec.crypto:CryptographyCodec", cacheble=False, password="", salt="")  # noqa: S106
