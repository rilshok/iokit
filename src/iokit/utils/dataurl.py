"""Decode `data:` URLs into state objects."""

__all__ = ["dataurl", "is_dataurl"]

import re
from functools import cache
from mimetypes import MimeTypes
from typing import Any
from urllib.parse import unquote_to_bytes

from iokit.dtype.data import Data
from iokit.dtype.extension import Extension
from iokit.state import LoadedState

_SCHEME = "data:"

#: The payload is base64 when the media type is closed by this marker.
_BASE64_MARKER = re.compile(r";[ \t]*base64[ \t]*$", re.IGNORECASE)

#: Whitespace base64 is wrapped in, and the URL-safe alphabet it is sometimes written in.
_BASE64_ALPHABET = str.maketrans("-_", "+/", " \t\n\r\f\v")

#: What a data URL carries when it names no media type of its own (RFC 2397).
_DEFAULT_MEDIA_TYPE = "text/plain"

#: The extension of a payload nothing tells the format of.
_FALLBACK = Extension.BIN

#: What a subtype has to read as to stand in for an extension.
_TOKEN = re.compile(r"[a-z0-9]{1,16}")

#: Prefixes of a subtype that say nothing about the format behind them.
_FACETS = ("x-", "x.")

#: Media types the standard library knows no extension for, or none that iokit reads.
_MEDIA_TYPES: dict[str, Extension] = {
    "application/gzip": Extension.GZ,
    "application/x-gzip": Extension.GZ,
    "application/x-jsonlines": Extension.JSONL,
    "application/x-ndjson": Extension.JSONL,
    "application/x-zip-compressed": Extension.ZIP,
    "audio/vnd.wave": Extension.WAV,
    "audio/wave": Extension.WAV,
    "image/x-icon": Extension.ICO,
}

#: Every extension iokit reads, to tell a guess worth taking from one worth nothing.
_KNOWN_EXTENSIONS = {extension.value for extension in Extension if extension.value}


@cache
def _mime_database() -> MimeTypes:
    """Serve the table of the standard library alone, which every host spells alike."""
    return MimeTypes()


def is_dataurl(url: str) -> bool:
    """Tell whether `url` carries its payload inline under the `data:` scheme.

    Args:
        url: The URL to look at; only its first few characters are read.

    Returns:
        Whether the URL opens with the `data:` scheme, written in any case.

    """
    return url[: len(_SCHEME)].lower() == _SCHEME


def _split(url: str) -> tuple[str, str, bool]:
    """Part a data URL into what it declares, what it carries, and how that is written."""
    if not is_dataurl(url):
        msg = "A data URL must open with the 'data:' scheme"
        raise ValueError(msg)
    body = url[len(_SCHEME) :].partition("#")[0]  # a fragment is no part of the payload
    header, comma, payload = body.partition(",")
    if not comma:
        msg = "A data URL must hold a comma parting its media type from its payload"
        raise ValueError(msg)
    header, marked = _BASE64_MARKER.subn("", header.strip())
    return header, payload, bool(marked)


def _payload(payload: str, *, base64: bool) -> Data:
    """Decode what a data URL carries, percent-encoding first and base64 over it."""
    raw = unquote_to_bytes(payload)
    if not base64:
        return Data(raw)
    # read past the whitespace, the missing padding, and the alphabet of a URL
    text = raw.decode("latin-1").translate(_BASE64_ALPHABET)
    try:
        return Data.from_base64(text + "=" * (-len(text) % 4))
    except ValueError as exc:  # `binascii.Error` among them
        msg = "The payload of a data URL is not valid base64"
        raise ValueError(msg) from exc


def _media_type(header: str) -> str:
    """Read the media type a data URL declares, defaulting the way the scheme has it."""
    declared = header.strip()
    if not declared or declared.startswith(";"):
        declared = _DEFAULT_MEDIA_TYPE + declared
    media_type = declared.partition(";")[0].strip().lower()
    kind, _, subtype = media_type.partition("/")
    if not kind or not subtype or "/" in subtype:
        return _DEFAULT_MEDIA_TYPE
    return media_type


def _parts(subtype: str) -> tuple[str, str]:
    """Part a subtype into its name and the structured syntax it is written in."""
    name, plus, syntax = subtype.rpartition("+")
    return (name, syntax) if plus else (subtype, "")


def _spelled(name: str) -> str:
    """Spell an extension out of the name of a subtype, as most of them carry one."""
    for facet in _FACETS:
        name = name.removeprefix(facet)
    return f".{name}" if _TOKEN.fullmatch(name) else ""


def _suffix(media_type: str) -> str:
    """Find the extension a payload of `media_type` is filed under."""
    if (filed := _MEDIA_TYPES.get(media_type)) is not None:
        return filed.value
    name, syntax = _parts(media_type.partition("/")[2])
    spelled = _spelled(name)
    guesses = [guess.lower() for guess in _mime_database().guess_all_extensions(media_type)]
    # an extension iokit reads first of all, so that a codec can be had for the payload
    if readable := [guess for guess in guesses if guess in _KNOWN_EXTENSIONS]:
        return spelled if spelled in readable else readable[0]
    if (written := f".{syntax}") in _KNOWN_EXTENSIONS:
        return spelled + written  # a format stacked on another, as `.epub.zip`
    # then the curated extension of the standard library, and the subtype for the rest
    return (guesses[0] if guesses else spelled) or _FALLBACK.value


def dataurl(url: str) -> LoadedState[Any]:
    """Decode a data URL into a state named by nothing but its extension.

    A data URL carries its payload inline and no name to file it under, so the state is
    left with a bare extension for a path, `.json` or `.jpeg` as the media type has it.

    Args:
        url: The data URL, of the form `data:[<media type>][;base64],<payload>`.

    Returns:
        The state the URL carries, timestamped as of now.

    Raises:
        ValueError: If `url` is no data URL, or its payload does not decode.

    """
    header, payload, base64 = _split(url)
    return LoadedState(
        _payload(payload, base64=base64),
        path=_suffix(_media_type(header)),
    )
