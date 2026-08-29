"""Base codec protocol and registry for encoding and decoding typed data."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from importlib import import_module
from typing import Any, BinaryIO, Generic, TypeVar

from packaging.requirements import Requirement

from iokit.dtype.extension import Extension
from iokit.utils.dependency import satisfies

T = TypeVar("T", bound=object)


class Codec(Generic[T]):
    """Convert between typed data and binary I/O streams."""

    def encode(self, data: T) -> BinaryIO:
        """Write `data` to a binary buffer."""
        raise NotImplementedError

    def decode(self, buffer: BinaryIO) -> T:
        """Read `buffer` and return typed data."""
        raise NotImplementedError


_CODEC_CACHE: dict[int, Codec[Any]] = {}

Requirements = str | Requirement | Iterable[str | Requirement]


def _requirements(requirements: Requirements | None) -> list[Requirement]:
    """Parse and normalize `requirements` for hashing."""
    if isinstance(requirements, str | Requirement):
        requirements = [requirements]
    return [Requirement(r) for r in sorted({str(r) for r in requirements or ()})]


def _suffix(extension: Extension | str) -> str:
    """Format `extension` as a lowercase dotted suffix."""
    suffix = extension.value if isinstance(extension, Extension) else extension
    suffix = suffix.strip().lower()
    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"
    return suffix


@dataclass
class CodecSpec:
    """Codec specification with extension and dependencies."""

    ext: Extension | str
    spec: str
    config: dict[str, Any]
    requirements: Requirements | None
    cacheble: bool

    def __post_init__(self) -> None:
        """Validate and normalize the specification."""
        if not self.module or not self.attribute:
            msg = f"Codec spec must read as 'module:attribute', got {self.spec!r}"
            raise ValueError(msg)

        self.ext = _suffix(self.ext)
        self.config = {name: self.config[name] for name in sorted(self.config)}
        self.requirements = _requirements(self.requirements)

        try:
            hash(self)
        except TypeError as exc:
            msg = f"Codec config values must be hashable, got {self.config}"
            raise TypeError(msg) from exc

    @property
    def suffix(self) -> str:
        """Return the file extension suffix."""
        return _suffix(self.ext)

    @property
    def module(self) -> str:
        """Return the module containing the codec class."""
        return self.spec.partition(":")[0]

    @property
    def attribute(self) -> str:
        """Return the codec class name in the module."""
        return self.spec.partition(":")[2]

    def __hash__(self) -> int:
        """Return hash of the specification."""
        state = (
            self.spec,
            tuple((k, hash(v)) for k, v in self.config.items()),
            tuple(str(r) for r in _requirements(self.requirements)),
        )
        return hash(state)

    def produce(self, **config: object) -> Codec[Any]:
        """Instantiate the codec class with merged config."""
        merged = self.config | config
        obj = replace(self, config={key: merged[key] for key in self.config})

        if cached := _CODEC_CACHE.get(hash(obj)):
            return cached

        if missing := [r for r in _requirements(obj.requirements) if not satisfies(r)]:
            req_str = ", ".join(str(r) for r in missing)
            install_cmd = "pip install " + " ".join(r.name for r in missing)
            msg = f"Missing required packages: {req_str}. Install with: {install_cmd}"
            raise ModuleNotFoundError(msg)

        module = import_module(obj.module)
        kls = getattr(module, obj.attribute)
        if not isinstance(kls, type) or not issubclass(kls, Codec):
            msg = f"Codec spec {obj.spec!r} must name a Codec subclass, got {kls!r}"
            raise TypeError(msg)
        produced: Codec[Any] = kls(**obj.config)
        if obj.cacheble:
            _CODEC_CACHE[hash(obj)] = produced
        return produced


_CODEC_REGISTRY: list[CodecSpec] = []


def registrate(
    ext: Extension | str,
    spec: str,
    requirements: Requirements | None = None,
    *,
    override: bool = False,
    cacheble: bool = True,
    **kwargs: object,
) -> None:
    """Register a codec for an extension.

    Args:
        ext: File extension.
        spec: Module and class in 'module:class' format.
        requirements: Package requirements.
        override: Check this codec first.
        cacheble: Cache codec instances.
        **kwargs: Codec configuration.

    """
    entry = CodecSpec(
        ext=ext,
        spec=spec,
        config=kwargs,
        requirements=requirements,
        cacheble=cacheble,
    )
    if override:
        _CODEC_REGISTRY.insert(0, entry)
    else:
        _CODEC_REGISTRY.append(entry)


def _candidates(name: str) -> Iterator[CodecSpec]:
    """Yield codecs matching `name` with longest extension."""
    matched = [codec for codec in _CODEC_REGISTRY if name.endswith(codec.suffix)]
    if not matched:
        msg = f"No codec registered for {name!r}"
        raise LookupError(msg)
    score = max(len(codec.suffix) for codec in matched)
    for codec in matched:
        if len(codec.suffix) == score:
            yield codec


def best_codec(name: str, **config: object) -> Codec[Any]:
    """Get the first matching codec with satisfied dependencies.

    Args:
        name: Filename to find codec for.
        **config: Codec configuration overrides.

    Returns:
        An instantiated codec.

    Raises:
        LookupError: No codec for extension.
        ModuleNotFoundError: Matching codecs lack dependencies.

    """
    failures: list[ModuleNotFoundError] = []
    for codec in _candidates(name.lower()):
        try:
            return codec.produce(**config)
        except ModuleNotFoundError as exc:  # noqa: PERF203
            failures.append(exc)

    if len(failures) == 1:
        raise failures[0]

    reasons = "; ".join(str(exc) for exc in failures)
    msg = (
        f"No codec for {name!r} could be created, all {len(failures)} candidates failed, "
        f"any one of them would do: {reasons}"
    )
    raise ModuleNotFoundError(msg) from failures[-1]


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
registrate(ext=Extension.YAML, spec="iokit.codec.yaml:YamlCodec", requirements="PyYAML>=6.0.1")
registrate(ext=Extension.YML, spec="iokit.codec.yaml:YamlCodec", requirements="PyYAML>=6.0.1")
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
    Extension.OGX: "Ogg",
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
