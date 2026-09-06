"""A state read straight from a `data:` URL, named by nothing but its media type."""

import json
import re
from typing import Any

import pytest
from PIL import Image as PillowImage

from iokit import Data, Json, Png, Txt
from iokit.utils.dataurl import dataurl
from iokit.utils.web import web

#: The red dot of the Wikipedia article on the scheme, five pixels across.
RED_DOT = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
    "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
)


def test_json_document_encoded_in_place() -> None:
    """A document written into a data URL comes back as the `.json` state it was."""
    document: dict[str, Any] = {"name": "iokit", "tags": ["io", "kit"], "size": 42}
    payload = Data(json.dumps(document).encode("utf-8"))
    url = f"data:application/json;base64,{payload.base64}"

    state = web(url)
    assert state.path == ".json"
    assert state.data == payload
    assert state.load() == document

    typed = web(url, Json)
    assert typed.path == ".json"
    assert typed.load() == document


def test_json_document_percent_encoded() -> None:
    """A data URL spells its payload out where it is not base64."""
    state = web("data:application/json,%7B%22a%22%3A%20%5B1%2C%202%5D%7D", Json)
    assert state.path == ".json"
    assert state.load() == {"a": [1, 2]}


def test_payload_of_a_picture() -> None:
    """A picture arrives under the extension of its media type, ready for its codec."""
    state = web(RED_DOT, Png)
    assert state.path == ".png"
    assert state.data[:4] == b"\x89PNG"
    picture = state.load()
    assert isinstance(picture, PillowImage.Image)
    assert picture.size == (5, 5)


def test_text_of_the_default_media_type() -> None:
    """A URL naming no media type carries plain text, the way the scheme has it."""
    state = web("data:,Hello%2C%20World%21", Txt)
    assert state.path == ".txt"
    assert state.load() == "Hello, World!"


@pytest.mark.parametrize(
    ("url", "path", "payload"),
    [
        # the examples of the MDN and Wikipedia articles on the scheme
        ("data:,Hello%2C%20World%21", ".txt", b"Hello, World!"),
        ("data:text/plain,Hello%2C%20%57%6F%72%6C%64%21", ".txt", b"Hello, World!"),
        ("data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==", ".txt", b"Hello, World!"),
        ("data:text/html,%3Ch1%3EHi%3C%2Fh1%3E", ".html", b"<h1>Hi</h1>"),
        ("data:text/plain;charset=UTF-8;page=21,the%20data:1", ".txt", b"the data:1"),
        ("data:text/vnd-example+xyz;foo=bar;base64,R0lGODdh", ".bin", b"GIF87a"),
        ("data:text/html,%3Cp%3Ehi%3C%2Fp%3E", ".html", b"<p>hi</p>"),
        ("data:image/jpeg;base64,/9j/4AAQSkZJRg==", ".jpeg", b"\xff\xd8\xff\xe0\x00\x10JFIF"),
        ("data:,", ".txt", b""),
        # a payload of its own may hold the commas and the query the header knows nothing of
        ("data:text/csv,a%2Cb%0A1%2C2", ".csv", b"a,b\n1,2"),
        ("data:text/plain,a?b=c", ".txt", b"a?b=c"),
        # the scheme, the marker, and the media type are all read without regard to case
        ("DATA:APPLICATION/JSON;BASE64,eyJhIjogMX0=", ".json", b'{"a": 1}'),
        # a media type of parameters alone still leaves the default one standing
        ("data:;base64,eyJhIjogMX0=", ".txt", b'{"a": 1}'),
        # nothing tells what an unnamed binary payload is, so it is filed as plain bytes
        ("data:application/octet-stream;base64,AAEC", ".bin", b"\x00\x01\x02"),
    ],
)
def test_examples_of_the_scheme(url: str, path: str, payload: bytes) -> None:
    """Each example of the scheme is read as the state it stands for."""
    state = web(url)
    assert state.path == path
    assert state.data == payload


@pytest.mark.parametrize(
    ("media_type", "path"),
    [
        # an extension iokit reads, spelled the way the subtype has it
        ("image/jpeg", ".jpeg"),
        ("image/png", ".png"),
        ("audio/mpeg", ".mp3"),
        ("text/tab-separated-values", ".tsv"),
        ("application/x-ndjson", ".jsonl"),
        # a structured syntax iokit reads, laid behind the name of the format itself
        ("application/ld+json", ".ld.json"),
        ("application/epub+zip", ".epub.zip"),
        ("application/vnd.acme.thing+json", ".json"),
        # the curated extension of the standard library, where it knows the media type
        ("application/msword", ".doc"),
        ("video/quicktime", ".mov"),
        ("text/x-python", ".py"),
        # the subtype itself, for the long tail the standard library says nothing of
        ("application/wasm", ".wasm"),
        ("image/svg+xml", ".svg"),
        ("font/woff2", ".woff2"),
        ("application/x-lz4", ".lz4"),
        # nothing that reads as an extension at all
        ("application/x-www-form-urlencoded", ".bin"),
        ("text/..%2F..%2Fetc%2Fpasswd", ".bin"),
    ],
)
def test_the_extension_a_media_type_is_filed_under(media_type: str, path: str) -> None:
    """A media type is filed under the extension it names, or under plain bytes."""
    assert web(f"data:{media_type},x").path == path


def test_a_structured_syntax_is_read_by_its_own_codec() -> None:
    """A format stacked on another is loaded by the codec of the syntax it is written in."""
    state = web("data:application/ld+json,%7B%22%40id%22%3A%20%22iokit%22%7D", Json)
    assert state.path == ".ld.json"
    assert state.load() == {"@id": "iokit"}


@pytest.mark.parametrize(
    "url",
    [
        "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==",  # as it is written
        "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ",  # the padding left off
        "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ%3D%3D",  # the padding encoded over
        "data:text/plain;base64,SGVsbG8s\n    IFdvcmxkIQ==",  # broken across lines
        "data:text/plain;  BASE64  ,SGVsbG8sIFdvcmxkIQ==",  # the marker spaced out
        "data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==#fragment",  # a fragment hung off it
    ],
)
def test_base64_read_forgivingly(url: str) -> None:
    """The base64 of a URL is read past the whitespace and padding it is written with."""
    assert web(url).data == b"Hello, World!"


def test_charset_leaves_the_payload_as_it_is() -> None:
    """The bytes are handed over as they are, for the codec to read in its own encoding."""
    text = "Привет, мир!"
    state = web(f"data:text/plain;charset=utf-8;base64,{Data(text.encode()).base64}", Txt)
    assert state.load() == text


@pytest.mark.parametrize(
    "url",
    [
        "data:text/plain",  # no comma parting the media type from the payload
        "data:",
        "data:text/plain#,payload",  # the comma is past the fragment, so past the URL
        "https://example.com/data.json",  # another scheme altogether
        "data:text/plain;base64,a",  # a base64 payload of a length no padding mends
    ],
)
def test_a_malformed_url_is_refused(url: str) -> None:
    """A URL the scheme cannot account for is refused rather than half read."""
    with pytest.raises(ValueError, match="data URL"):
        dataurl(url)


@pytest.mark.parametrize(
    "media_type",
    [
        "text/..%2F..%2Fetc%2Fpasswd",
        "text/" + "a" * 200,
        "image / png",
        "image%2Fpng",
        "text/x-",
        "text/+json",
        "text/json+json",
        "application/x.foo+zip",
        "text/$%^&*",
        "/",
        "text/",
        "/png",
    ],
)
def test_a_subtype_never_spells_more_than_an_extension(media_type: str) -> None:
    """Whatever a URL declares, the state is left with a well formed extension for a path."""
    assert re.fullmatch(r"(\.[a-z0-9]+){1,2}", web(f"data:{media_type},x").path)


def test_the_media_type_must_answer_the_expected_format() -> None:
    """A payload of another media type than the one asked for is no state of that format."""
    with pytest.raises(ValueError, match="extension"):
        web(RED_DOT, Json)
