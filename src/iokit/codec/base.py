import importlib.metadata as md
from collections.abc import Iterable
from dataclasses import dataclass, replace
from fnmatch import fnmatch
from importlib import import_module
from typing import Any, BinaryIO, Generic, TypeVar

from packaging.requirements import Requirement

T = TypeVar("T", bound=object)


class Codec(Generic[T]):
    def encode(self, data: T) -> BinaryIO:
        raise NotImplementedError

    def decode(self, buffer: BinaryIO) -> T:
        raise NotImplementedError


_WRAPPER_PREFIX = "*.*"


class Pattern(str):
    def __len__(self) -> int:
        return len(self.replace("*", ""))

    def __call__(self, string: str) -> bool:
        return fnmatch(name=string, pat=str(self))

    @property
    def wrapper(self) -> bool:
        """Whether the pattern, like `*.*.gz`, describes a container around another format."""
        return self.startswith(_WRAPPER_PREFIX)

    def unwrap(self, name: str) -> str:
        """Strip the container suffix, leaving the name of whatever the container holds."""
        return name.removesuffix(self.removeprefix(_WRAPPER_PREFIX))


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

    def produce(self, codec: Codec[Any] | None = None, /, **config: object) -> Codec[Any]:
        merged = self.config | config
        merged = {key: merged[key] for key in self.config}
        if codec is not None:
            # A wrapper codec is only as reusable as the codec it holds, so it is not cached.
            merged["codec"] = codec
        obj = replace(self, config=merged, cacheble=self.cacheble and codec is None)

        if cached := _CODEC_CACHE.get(hash(obj)):
            return cached

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
        produced: Codec[Any] = kls(**obj.config)
        if obj.cacheble:
            _CODEC_CACHE[hash(obj)] = produced
        return produced


_CODEC_REGISTRY: list[tuple[Pattern, CodecSpec]] = []


def registrate(
    pattern: str,
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
    if pattern == _WRAPPER_PREFIX:
        msg = f"Wrapper pattern {pattern!r} has no suffix left to unwrap"
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


registrate(pattern="*", spec="iokit.codec.bin:BinCodec")
registrate(pattern="*.bin", spec="iokit.codec.bin:BinCodec")
registrate(pattern="*.dat", spec="iokit.codec.bin:BinCodec")
registrate(
    pattern="*.json",
    spec="iokit.codec.json:JsonCodec",
    compact=False,
    ensure_ascii=False,
    allow_nan=False,
)
registrate(pattern="*.zip", spec="iokit.codec.zip:ZipCodec", buffered=False)
registrate(pattern="*.gz", spec="iokit.codec.gz:GzipCodec", compression=1)
registrate(pattern="*.*.gz", spec="iokit.codec.gz:GzipCodec", compression=1)
registrate(pattern="*.yaml", spec="iokit.codec.yaml:YamlCodec")
registrate(pattern="*.yml", spec="iokit.codec.yaml:YamlCodec")
registrate(pattern="*.txt", spec="iokit.codec.text:TextCodec", encoding="utf-8")
registrate(
    pattern="*.env",
    spec="iokit.codec.dotenv:DotenvCodec",
    requirements="python-dotenv>=1.0.1",
    encoding="utf-8",
    interpolate=False,
)
registrate(
    pattern="*.enc",
    spec="iokit.codec.crypto:CryptographyCodec",
    requirements="cryptography>=41.0.7",
    cacheble=False,
    password="",
    salt="",
)

_PILLOW_CODECS = {
    "jfif": "Jpeg",  # JPEG File Interchange Format
    "jpe": "Jpeg",  # variant extension
    "jpg": "Jpeg",
    "jpeg": "Jpeg",
    "bmp": "Bmp",
    "dib": "Dib",  # Device Independent Bitmap
    "gif": "Gif",
    "pbm": "Ppm",  # Portable Bitmap
    "pgm": "Ppm",  # Portable Graymap
    "ppm": "Ppm",  # Portable Pixmap
    "pnm": "Ppm",  # Portable Anymap (any format)
    "pfm": "Ppm",  # Portable FloatMap
    "png": "Png",
    "apng": "Png",  # Animated PNG
    "avif": "Avif",  # AV1 Image File Format
    "avifs": "Avif",  # AVIF sequence (animated)
    "blp": "Blp",  # Blizzard Picture (game assets)
    "cur": "Cur",  # Windows cursor (read-only)
    "pcx": "Pcx",  # ZSoft Paintbrush
    "dcx": "Dcx",  # Multi-page PCX
    "dds": "Dds",  # DirectDraw Surface (DirectX textures)
    "fli": "Fli",  # Autodesk Animator animation
    "flc": "Fli",  # Autodesk Animator animation variant
    "ftc": "Ftex",  # Fabrik Texture
    "ftu": "Ftex",  # Fabrik Texture variant
    "gbr": "Gbr",  # GIMP brush file
    "jp2": "Jpeg2000",  # JPEG 2000
    "j2k": "Jpeg2000",  # JPEG 2000 codestream
    "jpc": "Jpeg2000",  # JPEG 2000 codestream
    "jpf": "Jpeg2000",  # JPEG 2000 file
    "jpx": "Jpeg2000",  # JPEG 2000 extended
    "j2c": "Jpeg2000",  # JPEG 2000 codestream
    "icns": "Icns",  # macOS icon
    "ico": "Ico",  # Windows icon
    "im": "Im",  # GEOS Image
    "tif": "Tiff",
    "tiff": "Tiff",
    "mpo": "Mpo",  # Multi-Picture Object (Canon, Fujifilm)
    "msp": "Msp",  # Microsoft Paint bitmap
    "palm": "Palm",  # Palm Pilot bitmap
    "pcd": "Pcd",  # Kodak PhotoCD
    "pxr": "Pixar",  # Pixar texture
    "psd": "Psd",  # Adobe Photoshop (read-only)
    "qoi": "Qoi",  # Quite OK Image Format
    "bw": "Sgi",  # SGI black and white
    "rgb": "Sgi",  # SGI 3 color channels
    "rgba": "Sgi",  # SGI 3 color channels and alpha
    "sgi": "Sgi",  # SGI Image File Format
    "int": "Sgi",  # SGI black and white integer
    "inta": "Sgi",  # SGI black and white with alpha
    "ras": "Sun",  # Sun Raster
    "tga": "Tga",  # Targa/TARGA image
    "icb": "Tga",  # Targa (inverted)
    "vda": "Tga",  # Targa variant
    "vst": "Tga",  # Targa variant
    "webp": "Webp",
    "wmf": "Wmf",  # Windows Metafile
    "emf": "Wmf",  # Enhanced Metafile (Windows)
    "xbm": "Xbm",  # X11 Bitmap
    "xpm": "Xpm",  # X11 Pixmap
}

for _extension, _format in _PILLOW_CODECS.items():
    registrate(
        pattern=f"*.{_extension}",
        spec=f"iokit.codec.pillow:{_format}PillowCodec",
        requirements="Pillow>=10.4.0",
    )
