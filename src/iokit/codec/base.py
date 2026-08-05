from collections.abc import Iterable
from dataclasses import dataclass, replace
from importlib import import_module
from typing import Any, BinaryIO, Generic, TypeVar

from packaging.requirements import Requirement

from iokit.dtype.extension import Extension
from iokit.utils.dependency import satisfies
from iokit.utils.pattern import Pattern

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

    def produce(self, codec: Codec[Any] | None = None, /, **config: object) -> Codec[Any]:
        merged = self.config | config
        merged = {key: merged[key] for key in self.config}
        if codec is not None:
            # A wrapper codec is only as reusable as the codec it holds, so it is not cached.
            merged["codec"] = codec
        obj = replace(self, config=merged, cacheble=self.cacheble and codec is None)

        if cached := _CODEC_CACHE.get(hash(obj)):
            return cached

        requirements = [r for r in obj.requirements if not satisfies(r)]
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
        produced: Codec[Any] = kls(**obj.config)
        if obj.cacheble:
            _CODEC_CACHE[hash(obj)] = produced
        return produced


_CODEC_REGISTRY: list[tuple[Pattern, CodecSpec]] = []


def registrate(
    pattern: Pattern,
    spec: str,
    requirements: str | Iterable[str] | None = None,
    *,
    override: bool = False,
    cacheble: bool = True,
    **kwargs: object,
) -> None:
    if isinstance(requirements, str):
        requirements = [requirements]
    requirements = set(requirements or ())
    if pattern.lower() != pattern:
        msg = ""
        raise ValueError(msg)
    module, _, attr = spec.partition(":")
    if not module or not attr:
        msg = ""
        raise ValueError(msg)
    entry = (
        pattern,
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
    missing = [r for r in spec.requirements if not satisfies(r)]
    codec = f"{spec.module}:{spec.attriute}"
    if not missing:
        return f"{codec} (module {spec.module!r} is not importable)"
    packages = " ".join(sorted({r.name for r in missing}))
    return f"{codec}: pip install {packages}"


def _candidates(name: str) -> list[tuple[Pattern, CodecSpec]]:
    """Registry entries claiming the name, narrowed down to the most specific patterns."""
    matched = [(pattern, spec) for pattern, spec in _CODEC_REGISTRY if pattern(name)]
    if not matched:
        msg = f"No codec registered for {name!r}"
        raise LookupError(msg)
    score = max(len(pattern) for pattern, _ in matched)
    return [(pattern, spec) for pattern, spec in matched if len(pattern) == score]


def best_codec(name: str, **config: object) -> Codec[Any]:
    name = name.lower()
    failures: list[tuple[CodecSpec, ModuleNotFoundError]] = []
    for pattern, spec in _candidates(name):
        # a wrapper takes over the suffix it matched and delegates the rest of the name, so
        # `data.json.gz` resolves to a gzip codec holding the codec of `data.json`.
        try:
            codec = best_codec(pattern.unwrap(name), **config) if pattern.wrapper else None
            return spec.produce(codec, **config)
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


registrate(pattern=Pattern("*"), spec="iokit.codec.bin:BinCodec")
registrate(pattern=Extension.BIN.pattern, spec="iokit.codec.bin:BinCodec")
registrate(pattern=Extension.DAT.pattern, spec="iokit.codec.bin:BinCodec")
registrate(
    pattern=Extension.JSON.pattern,
    spec="iokit.codec.json:JsonCodec",
    compact=False,
    ensure_ascii=False,
    allow_nan=False,
)
registrate(
    pattern=Extension.JSONL.pattern,
    spec="iokit.codec.jsonl:JsonlCodec",
    requirements="jsonlines>=4.0.0",
    compact=True,
    ensure_ascii=False,
    allow_nan=False,
)
registrate(pattern=Extension.ZIP.pattern, spec="iokit.codec.zip:ZipCodec", buffered=False)
registrate(pattern=Extension.TAR.pattern, spec="iokit.codec.tar:TarCodec", buffered=False)
registrate(pattern=Extension.GZ.pattern, spec="iokit.codec.gz:GzipCodec", compression=1)
registrate(pattern=Extension.GZ.pattern_wrapper, spec="iokit.codec.gz:GzipCodec", compression=1)
registrate(pattern=Extension.YAML.pattern, spec="iokit.codec.yaml:YamlCodec")
registrate(pattern=Extension.YML.pattern, spec="iokit.codec.yaml:YamlCodec")
registrate(pattern=Extension.TXT.pattern, spec="iokit.codec.text:TextCodec", encoding="utf-8")
registrate(
    pattern=Extension.ENV.pattern,
    spec="iokit.codec.dotenv:DotenvCodec",
    requirements="python-dotenv>=1.0.1",
    encoding="utf-8",
    interpolate=False,
)
registrate(
    pattern=Extension.NPY.pattern,
    spec="iokit.codec.numpy:NumpyCodec",
    requirements="numpy>=1.21.1",
    allow_pickle=False,
)
registrate(
    pattern=Extension.NPZ.pattern,
    spec="iokit.codec.numpy:CompressedNumpyCodec",
    requirements="numpy>=1.21.1",
    allow_pickle=False,
)
registrate(
    pattern=Extension.CSV.pattern,
    spec="iokit.codec.pandas:CsvCodec",
    requirements="pandas>=1.5.3",
    encoding="utf-8",
    index=False,
)
registrate(
    pattern=Extension.TSV.pattern,
    spec="iokit.codec.pandas:TsvCodec",
    requirements="pandas>=1.5.3",
    encoding="utf-8",
    index=False,
)
registrate(
    pattern=Extension.ENC.pattern,
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
        pattern=_extension.pattern,
        spec=f"iokit.codec.soundfile:{_prefix}SoundfileCodec",
        requirements=["soundfile>=0.12.1", "numpy>=1.21.1"],
        subtype=None,
    )
    registrate(
        pattern=_extension.pattern,
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
        pattern=_extension.pattern,
        spec=f"iokit.codec.pillow:{_format}PillowCodec",
        requirements="Pillow>=10.4.0",
    )
