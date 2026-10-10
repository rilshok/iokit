# iokit

[![PyPI](https://img.shields.io/pypi/v/iokit)](https://pypi.org/project/iokit/)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Frilshok%2Fiokit%2Fmain%2Fpyproject.toml)](https://pypi.org/project/iokit/)
[![License](https://img.shields.io/pypi/l/iokit)](https://github.com/rilshok/iokit/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/rilshok/iokit?style=social)](https://github.com/rilshok/iokit)

iokit gives files of different formats one interface. A file is a `State`: a path, a modification time and the bytes behind them. The extension of the path decides how the bytes turn into a Python object and back, so a JSON config, a CSV table, an image or a tar archive are all read with `load()` and written to disk with `save()`. The same states go into archives and storages, S3 included.

```python
from iokit import Json, file

config = {"lr": 3e-4, "epochs": 10}

Json(config, "config").save(".", force=True)
print(file("config.json").load())  # {'lr': 0.0003, 'epochs': 10}
```

## Installation

```bash
pip install iokit
```

The core needs four small packages and covers txt, json, bin, dat, gz, tar and zip. Everything else is an extra: `yaml`, `jsonl`, `env`, `crypto`, `numpy`, `pandas`, `image`, `audio`, `web` and `s3`, or `ultra` for all of them.

```bash
pip install "iokit[pandas,image]"
```

If a format's package is missing, iokit names the package to install the first time the format is used. `web()`, `S3Storage` and `Waveform` fail with the usual `ModuleNotFoundError` instead.

## Reading and writing

Creating a format state such as `Json(...)` serializes the payload in memory. `save(root)` writes it at its own path under `root` and creates the directories on the way. An existing file is replaced only with `force=True`.

```python
from iokit import Json

settings = {"key": "value"}

state = Json(settings, "configs/app")
print(state)  # configs/app.json (16B)
print(state.load())  # {'key': 'value'}
state.save(".", force=True)
```

`file(path)` opens a file that is already on disk. Its content is not read until `.load()`, `size` comes from the file system, and `digest` reads the file in chunks. `file("message.txt", Txt)` checks the extension and returns a `Txt`, which reads the file into memory right away.

```python
from iokit import Txt, file

text = "Hello, World!"
Txt(text, "message").save(".", force=True)

state = file("message.txt")
print(state.size)  # 13
print(state.load())  # Hello, World!
```

## Formats

| Class | `.load()` returns | Extra |
|---|---|---|
| `Txt` | `str` | |
| `Json` | `dict`, `list`, `str`, `int`, `float`, `bool` or `None` | |
| `Bin`, `Dat` | `bytes` | |
| `Zip`, `Tar` | an iterator of member states | |
| `Gzip` | the state under the compression | |
| `Enc` | the state under the encryption | `crypto` |
| `Jsonl` | a `list`, one item per line | `jsonl` |
| `Yaml`, `Yml` | `dict`, `list` or `str` | `yaml` |
| `Env` | `dict[str, str \| None]` | `env` |
| `Csv`, `Tsv` | `pandas.DataFrame` | `pandas` |
| `Npy` | `numpy.ndarray` | `numpy` |
| `Png`, `Jpeg`, `Jpg` | `PIL.Image.Image` | `image` |
| `Wav`, `Flac`, `Mp3`, `Ogg`, `Oga`, `Ogx`, `Opus` | `Waveform` | `audio` |

The extension is the class name in lowercase, except for `Gzip`, which is `.gz`. `file(path).load()` also reads `.npz` as a dict of arrays and about 60 image extensions known to Pillow, such as `.webp`, `.tiff` and `.gif`.

## Compression and encryption

`gzip()` and `encrypt()` wrap a state in a layer and add `.gz` or `.enc` to its path. Loading a layer gives back the state under it, so every layer takes one more `.load()`.

```python
from iokit import Json

predicts = [{"label": "cat", "score": 0.97}] * 10_000

state = Json(predicts, "predicts")
packed = state.gzip(compression=9)
print(state, "->", packed)  # predicts.json (322.3K) -> predicts.json.gz (1.0K)
print(packed.load())  # predicts.json (322.3K)
print(packed.load().load()[0])  # {'label': 'cat', 'score': 0.97}
```

```python
# pip install "iokit[crypto]"
from iokit import Json

credentials = {"token": "abc"}

secret = Json(credentials, "credentials").gzip().encrypt(password="pa$$")
print(secret.path)  # credentials.json.gz.enc
print(secret.load(password="pa$$").load().load())  # {'token': 'abc'}
```

A `predicts.json.gz` on disk opens the same way: `file("predicts.json.gz").load().load()`.

## Archives

`Tar` and `Zip` keep the paths of their members and their modification times, to the precision the archive format allows. Loading an archive yields the members as states, and `filtrate` and `first` pick them by a glob pattern.

```python
from iokit import Json, Tar, Txt, filtrate, first

states = [
    Txt("first", "notes/a"),
    Txt("second", "notes/b"),
    Json({"n": 2}, "meta"),
]

archive = Tar(states, "bundle")
members = list(archive.load())
print(members)  # [notes/a.txt (5B), notes/b.txt (6B), meta.json (8B)]
print([state.path for state in filtrate(members, "notes/*")])  # ['notes/a.txt', 'notes/b.txt']
print(first(members, "*.json").load())  # {'n': 2}
```

`archive.gzip()` makes `bundle.tar.gz` out of it, and the JSON files of a directory are packed with `Tar(map(FileState, Path("data").rglob("*.json")), "data")`.

## Downloads

`web(url)` downloads a file into memory and names the state after the last part of the URL path. A `data:` URL is decoded locally, needs no extra, and gets only the extension of its media type as a path.

```python
# pip install "iokit[web]"
from iokit import web

iris_url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"
data_url = "data:application/json;base64,eyJhIjogMX0="

iris = web(iris_url)
print(iris)  # iris.csv (3.8K)

inline = web(data_url)
print(inline.path, inline.load())  # .json {'a': 1}
```

## Hashes and encodings

`digest(algorithm)` reads the content in chunks, so a large file never has to fit in memory. The result is `Data`, a `bytes` subclass with `hex()`, `base64`, `base64url` and `base32crockford`.

```python
from iokit import Txt

text = "Hello, World!"

state = Txt(text, "message")
print(state.digest("sha256").hex())  # dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f
print(state.digest("xxh64").base64url)  # xJqs-AgP5H8
print(state.data.base64)  # SGVsbG8sIFdvcmxkIQ==
```

The algorithms are `md5`, `sha1`, `sha224`, `sha256`, `sha384`, `sha512`, `sha3_224`, `sha3_256`, `sha3_384`, `sha3_512`, `blake2b`, `blake2s`, `xxh32`, `xxh64`, `xxh128`, `xxh3_64` and `xxh3_128`.

## Tables and audio

Tables, arrays, images and audio are created and loaded the same way as `Json`, only the payload differs. Two of them are worth a closer look. `Csv` writes no index column by default, unlike `DataFrame.to_csv`:

```python
# pip install "iokit[pandas]"
import pandas as pd
from iokit import Csv

frame = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})
state = Csv(frame, "table")
print(state.data.decode())
print(state.load().equals(frame))
```

```text
x,y
1,a
2,b

True
```

Audio loads into a `Waveform`, which holds the samples as a float32 array of shape `(frames, channels)` and shows up as a player in Jupyter:

```python
# pip install "iokit[audio]"
import numpy as np
from iokit import Waveform

t = np.linspace(0, 1, 16_000, endpoint=False)
samples = np.sin(2 * np.pi * 440 * t)

tone = Waveform(samples, freq=16_000)

audio = tone.to_flac("tone").load()
print(audio.freq, audio.channels, audio.duration)  # 16000 1 1.0
print(audio.cut(0.25, 0.75).duration)  # 0.5
```

## Storage

A storage keeps records under uids, relative paths such as `runs/01/metrics.json`, with `push`, `pull`, `remove`, `exists`, `size` and `index`. `LocalStorage`, `MemoryStorage` and `S3Storage` keep bytes, and their `Stream*` counterparts keep binary streams. `StateStorage` sits on top of a byte storage and keeps Python objects, encoded by the extension of the uid and optionally compressed and encrypted. `CachedStorage(hot, cold)` puts a fast storage in front of a slow one.

```python
from iokit import MemoryStorage, StateStorage

uid = "runs/01/metrics.json"
metrics = {"accuracy": 0.93}

storage = StateStorage(MemoryStorage(), compression=6)
storage.push(uid, metrics)
print(storage.pull(uid))  # {'accuracy': 0.93}
print(list(storage.index(prefix="runs/")))  # ['runs/01/metrics.json']
```

Swapping `MemoryStorage()` for `LocalStorage("cache")` or `S3Storage(...)` changes only where the records end up. `S3Storage` takes `access_key`, `secret_access_key`, `endpoint_url` and `region_name` for AWS or an S3-compatible service, and reads public buckets anonymously when given none of them:

```python
# pip install "iokit[s3]"
from iokit import S3Storage, StateStorage

bucket = "openaq-data-archive"
folder = "records/csv.gz/locationid=2178/year=2022"

s3 = StateStorage(S3Storage(bucket, folder))
uid = sorted(s3.index(prefix="month=05/"))[0]
print(uid)  # month=05/location-2178-20220503.csv.gz
print(s3.pull(uid))  # month=05/location-2178-20220503.csv (11.8K)
```

## Your own types

A format class can carry a payload of your own: subclass it with the payload as the type parameter and override `dump` and `parse`.

```python
from dataclasses import asdict, dataclass
from typing import Any

from iokit import Json


@dataclass
class Box:
    label: str
    xyxy: list[int]


class BoxJson(Json[Box]):
    def dump(self, data: Box) -> dict[str, Any]:
        return asdict(data)

    def parse(self, data: dict[str, Any]) -> Box:
        return Box(**data)


box = Box("car", [10, 20, 110, 80])

state = BoxJson(box, "box")
print(state.data.decode())  # {"label": "car", "xyxy": [10, 20, 110, 80]}
print(state.load())  # Box(label='car', xyxy=[10, 20, 110, 80])
```

On disk it is an ordinary `box.json`, and `load()` returns a `Box` both at runtime and for the type checker. `Csv`, `Npy`, `Yaml` and the other data formats can be subclassed the same way.

## Your own formats

A codec turns a binary stream into a payload and back. `registrate` binds it to an extension by its `module:class` path, and a class defined in a script or a notebook lives in `__main__`. A codec that only reads can leave `encode` out.

```python
from configparser import ConfigParser
from pathlib import Path
from typing import BinaryIO

from iokit import file
from iokit.codec.base import Codec, registrate


class IniCodec(Codec[dict[str, dict[str, str]]]):
    def decode(self, buffer: BinaryIO) -> dict[str, dict[str, str]]:
        parser = ConfigParser()
        with buffer:
            parser.read_string(buffer.read().decode())
        return {name: dict(parser[name]) for name in parser.sections()}


registrate(".ini", "__main__:IniCodec")

ini = "[server]\nport = 8080\n"
Path("app.ini").write_text(ini)

print(file("app.ini").load())  # {'server': {'port': '8080'}}
```

## Development

```bash
git clone https://github.com/rilshok/iokit
cd iokit
uv sync --extra dev
uvx pre-commit install
uv run pytest -n auto -m "not network"
```

## License

MIT
