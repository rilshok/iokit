from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from importlib import import_module
from typing import Any, BinaryIO, Generic, TypeVar

from packaging.requirements import Requirement

from iokit.dtype.extension import Extension
from iokit.utils.dependency import satisfies

T = TypeVar("T", bound=object)


class Codec(Generic[T]):
    def encode(self, data: T) -> BinaryIO:
        raise NotImplementedError

    def decode(self, buffer: BinaryIO) -> T:
        raise NotImplementedError


def _hashable(value: object) -> bool:
    try:
        hash(value)
    except TypeError:
        return False
    return True


_CODEC_CACHE: dict[int, Codec[Any]] = {}

Requirements = str | Requirement | Iterable[str | Requirement]


def _requirements(requirements: Requirements | None) -> list[Requirement]:
    """The named requirements as parsed `Requirement`s, deduplicated and ordered for hashing."""
    if isinstance(requirements, str | Requirement):
        requirements = [requirements]
    return [Requirement(r) for r in sorted({str(r) for r in requirements or ()})]


@dataclass
class CodecSpec:
    module: str
    attriute: str
    config: dict[str, Any]
    requirements: Requirements | None
    cacheble: bool

    def __post_init__(self) -> None:
        unhashable = [name for name, value in self.config.items() if not _hashable(value)]
        if unhashable:
            names = ", ".join(f"{name}={self.config[name]!r}" for name in sorted(unhashable))
            msg = f"Codec config values must be hashable, got unhashable: {names}"
            raise TypeError(msg)

        self.config = {name: self.config[name] for name in sorted(self.config)}
        self.requirements = _requirements(self.requirements)

    def __hash__(self) -> int:
        state = (
            self.module,
            self.attriute,
            tuple((k, hash(v)) for k, v in self.config.items()),
            tuple(str(r) for r in _requirements(self.requirements)),
        )
        return hash(state)

    def missing(self) -> list[Requirement]:
        """The requirements this spec names that the environment does not satisfy."""
        return [r for r in _requirements(self.requirements) if not satisfies(r)]

    def produce(self, **config: object) -> Codec[Any]:
        merged = self.config | config
        merged = {key: merged[key] for key in self.config}
        obj = replace(self, config=merged)

        if cached := _CODEC_CACHE.get(hash(obj)):
            return cached

        if missing := obj.missing():
            req_str = ", ".join(str(r) for r in missing)
            install_cmd = "pip install " + " ".join(r.name for r in missing)
            msg = f"Missing required packages: {req_str}. Install with: {install_cmd}"
            raise ModuleNotFoundError(msg)

        module = import_module(obj.module)
        kls = getattr(module, obj.attriute)
        if not issubclass(kls, Codec):
            msg = ""
            raise TypeError(msg)
        produced: Codec[Any] = kls(**obj.config)
        if obj.cacheble:
            _CODEC_CACHE[hash(obj)] = produced
        return produced


_CODEC_REGISTRY: list[tuple[str, CodecSpec]] = []


def _suffix(extension: Extension | str) -> str:
    """The extension as it trails a name: lowercase and dotted, `""` standing for any name."""
    suffix = extension.value if isinstance(extension, Extension) else extension
    suffix = suffix.strip().lower()
    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"
    return suffix


def registrate(
    ext: Extension | str,
    spec: str,
    requirements: Requirements | None = None,
    *,
    override: bool = False,
    cacheble: bool = True,
    **kwargs: object,
) -> None:
    module, _, attr = spec.partition(":")
    if not module or not attr:
        msg = ""
        raise ValueError(msg)
    entry = (
        _suffix(ext),
        CodecSpec(
            module=module,
            attriute=attr,
            config=kwargs,
            requirements=requirements,
            cacheble=cacheble,
        ),
    )
    if override:
        _CODEC_REGISTRY.insert(0, entry)
    else:
        _CODEC_REGISTRY.append(entry)


def _install_hint(codec: CodecSpec) -> str:
    missing = codec.missing()
    spec = f"{codec.module}:{codec.attriute}"
    if not missing:
        return f"{spec} (module {codec.module!r} is not importable)"
    packages = " ".join(sorted({r.name for r in missing}))
    return f"{spec}: pip install {packages}"


def _candidates(name: str) -> Iterator[CodecSpec]:
    """Registry entries claiming the name, narrowed down to the longest extensions."""
    matched = [(ext, spec) for ext, spec in _CODEC_REGISTRY if name.endswith(ext)]
    if not matched:
        msg = f"No codec registered for {name!r}"
        raise LookupError(msg)
    score = max(len(ext) for ext, _ in matched)
    for ext, spec in matched:
        if len(ext) == score:
            yield spec


def best_codec(name: str, **config: object) -> Codec[Any]:
    name = name.lower()
    failures: list[tuple[CodecSpec, ModuleNotFoundError]] = []
    for spec in _candidates(name):
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


registrate(ext=Extension.NULL, spec="iokit.codec.bin:BinCodec")
registrate(ext=Extension.BIN, spec="iokit.codec.bin:BinCodec")
registrate(ext=Extension.DAT, spec="iokit.codec.bin:BinCodec")
registrate(
    ext=Extension.JSON,
    spec="iokit.codec.json:JsonCodec",
    compact=False,
    ensure_ascii=False,
    allow_nan=False,
)
registrate(
    ext=Extension.JSONL,
    spec="iokit.codec.jsonl:JsonlCodec",
    requirements="jsonlines>=4.0.0",
    compact=True,
    ensure_ascii=False,
    allow_nan=False,
)
registrate(ext=Extension.ZIP, spec="iokit.codec.zip:ZipCodec", buffered=False)
registrate(ext=Extension.TAR, spec="iokit.codec.tar:TarCodec", buffered=False)
registrate(ext=Extension.GZ, spec="iokit.codec.gz:GzipCodec", compression=1)
registrate(ext=Extension.YAML, spec="iokit.codec.yaml:YamlCodec")
registrate(ext=Extension.YML, spec="iokit.codec.yaml:YamlCodec")
registrate(ext=Extension.TXT, spec="iokit.codec.text:TextCodec", encoding="utf-8")
registrate(
    ext=Extension.ENV,
    spec="iokit.codec.dotenv:DotenvCodec",
    requirements="python-dotenv>=1.0.1",
    encoding="utf-8",
    interpolate=False,
)
registrate(
    ext=Extension.NPY,
    spec="iokit.codec.numpy:NumpyCodec",
    requirements="numpy>=1.21.1",
    allow_pickle=False,
)
registrate(
    ext=Extension.NPZ,
    spec="iokit.codec.numpy:CompressedNumpyCodec",
    requirements="numpy>=1.21.1",
    allow_pickle=False,
)
registrate(
    ext=Extension.CSV,
    spec="iokit.codec.pandas:CsvCodec",
    requirements="pandas>=1.5.3",
    encoding="utf-8",
    index=False,
)
registrate(
    ext=Extension.TSV,
    spec="iokit.codec.pandas:TsvCodec",
    requirements="pandas>=1.5.3",
    encoding="utf-8",
    index=False,
)
registrate(
    ext=Extension.ENC,
    spec="iokit.codec.crypto:CryptographyCodec",
    requirements="cryptography>=41.0.7",
    cacheble=False,
    password="",
    salt="",
)

_AUDIO_CODECS = {
    Extension.WAV: "Wav",
    Extension.FLAC: "Flac",
    Extension.MP3: "Mp3",
    Extension.OGG: "Ogg",
    Extension.OGA: "Ogg",  # `.oga` is an ogg container, told apart only by its extension
    Extension.OPUS: "Opus",
}

for _extension, _prefix in _AUDIO_CODECS.items():
    # Both backends claim the same patterns, and the first registered one wins as long as its
    # dependencies are installed, so soundfile is the default and torchaudio the fallback.
    registrate(
        ext=_extension,
        spec=f"iokit.codec.soundfile:{_prefix}SoundfileCodec",
        requirements=["soundfile>=0.12.1", "numpy>=1.21.1"],
        subtype=None,
    )
    registrate(
        ext=_extension,
        spec=f"iokit.codec.torchaudio:{_prefix}TorchaudioCodec",
        requirements=["torchaudio>=2.0.0", "numpy>=1.21.1"],
    )

_PILLOW_CODECS = {
    Extension.JFIF: "Jpeg",
    Extension.JPE: "Jpeg",
    Extension.JPG: "Jpeg",
    Extension.JPEG: "Jpeg",
    Extension.BMP: "Bmp",
    Extension.DIB: "Dib",
    Extension.GIF: "Gif",
    Extension.PBM: "Ppm",
    Extension.PGM: "Ppm",
    Extension.PPM: "Ppm",
    Extension.PNM: "Ppm",
    Extension.PFM: "Ppm",
    Extension.PNG: "Png",
    Extension.APNG: "Png",
    Extension.AVIF: "Avif",
    Extension.AVIFS: "Avif",
    Extension.BLP: "Blp",
    Extension.CUR: "Cur",
    Extension.PCX: "Pcx",
    Extension.DCX: "Dcx",
    Extension.DDS: "Dds",
    Extension.FLI: "Fli",
    Extension.FLC: "Fli",
    Extension.FTC: "Ftex",
    Extension.FTU: "Ftex",
    Extension.GBR: "Gbr",
    Extension.JP2: "Jpeg2000",
    Extension.J2K: "Jpeg2000",
    Extension.JPC: "Jpeg2000",
    Extension.JPF: "Jpeg2000",
    Extension.JPX: "Jpeg2000",
    Extension.J2C: "Jpeg2000",
    Extension.ICNS: "Icns",
    Extension.ICO: "Ico",
    Extension.IM: "Im",
    Extension.TIF: "Tiff",
    Extension.TIFF: "Tiff",
    Extension.MPO: "Mpo",
    Extension.MSP: "Msp",
    Extension.PALM: "Palm",
    Extension.PCD: "Pcd",
    Extension.PXR: "Pixar",
    Extension.PSD: "Psd",
    Extension.QOI: "Qoi",
    Extension.BW: "Sgi",
    Extension.RGB: "Sgi",
    Extension.RGBA: "Sgi",
    Extension.SGI: "Sgi",
    Extension.INT: "Sgi",
    Extension.INTA: "Sgi",
    Extension.RAS: "Sun",
    Extension.TGA: "Tga",
    Extension.ICB: "Tga",
    Extension.VDA: "Tga",
    Extension.VST: "Tga",
    Extension.WEBP: "Webp",
    Extension.WMF: "Wmf",
    Extension.EMF: "Wmf",
    Extension.XBM: "Xbm",
    Extension.XPM: "Xpm",
}

for _extension, _format in _PILLOW_CODECS.items():
    registrate(
        ext=_extension,
        spec=f"iokit.codec.pillow:{_format}PillowCodec",
        requirements="Pillow>=10.4.0",
    )
