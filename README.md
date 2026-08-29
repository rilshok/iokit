# iokit

Python library for serialization and file operations. Unifies multiple format codecs (JSON, YAML, Tar, etc.) with a single State interface that combines data, path, and timestamp.

## Installation

Base install covers txt, bin, dat, json, gz, zip, tar:

```bash
pip install iokit
```

For all formats and web download support:

```bash
pip install iokit[ultra]
```

Missing formats will tell you what to install:

```python
from iokit import Yaml
Yaml({"key": "value"}, "file")
```

```plain-text
ModuleNotFoundError: Missing required packages: PyYAML>=6.0.1. Install with: pip install PyYAML
```

## Quick Start

Work with data as States. Each State carries the data, a path, and a timestamp. Load and save without thinking about formats.

JSON file:

```python
from iokit import Json

state = Json({"key": "value"}, path="config.json")
print(state.path)      # config.json
print(state.size)      # 16
print(state.load())    # {'key': 'value'}
```

Text file:

```python
from iokit import Txt

state = Txt("Hello, World!", "message")
state.save("/tmp/data", parents=True)
```

Load any file from disk:

```python
from iokit import file

state = file("/path/to/file.txt")
content = state.load()
```

## Common Operations

Chain transformations:

```python
from iokit import Txt

state = Txt("Secret data", "notes")
encrypted = state.encrypt(password="secret")
compressed = encrypted.gzip()
compressed.save("/tmp")
```

Load compressed:

```python
loaded = encrypted.load(password="secret").load()
```

Archives:

```python
from iokit import Tar, Txt

file1 = Txt("First", "a")
file2 = Txt("Second", "b")

archive = Tar([file1, file2], "bundle")
states = list(archive.load())
```

Find states by pattern:

```python
from iokit import filtrate, first

results = filtrate(archive.load(), "*.txt")
first_match = first(archive.load(), "a*")
```

Download:

```python
from iokit import web

state = web("https://example.com/data.json", Json)
data = state.load()
```

Checksum:

```python
state.digest("sha256").base64
state.digest("xxh128").base64url
```

## Storage

Store and retrieve records by uid:

```python
from iokit.storage import LocalStorage

storage = LocalStorage("/data")
storage.push("records/data.json", data)

loaded = storage.pull("records/data.json")
storage.remove("records/data.json")

for uid in storage.index(prefix="records/"):
    print(uid)
```

State-aware storage with automatic encoding:

```python
from iokit.storage import StateStorage

storage = StateStorage(
    LocalStorage("/data"),
    compression=6,
    password="secret"
)

storage.push("file.json", {"data": 123})
result = storage.pull("file.json")
```

## Contributing

Found a bug or have an idea? Open an issue or submit a pull request.

## License

MIT
