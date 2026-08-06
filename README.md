# I/O Kit Python Library

IOKit is a Python library that offers a suite of utilities for managing a wide range of input/output operations. Central to its design is the concept of a `State`: a unit of data that carries a path and a timestamp, and that can be loaded, saved, or transformed. Every state stands for a valid file, whether it is held in memory or read from disk on demand.

IOKit abstracts and unifies serialization and deserialization operations from various libraries into a single, cohesive interface. This allows for direct manipulation of the file's state in memory, eliminating the need for disk interaction. Consequently, it facilitates the (de)serialization of data in multiple formats, such as `json`, `yaml`, `txt`, `tar`, `gzip`, among others.

## Installation

You can install the IOkit library using pip:

```bash
pip install iokit
```

The base install carries no third-party backends, and covers `txt`, `bin`, `dat`, `json`, `gz`, `zip`, and `tar`. Every other format, along with downloading over `web`, rests on an optional dependency, all of which come with the `ultra` extra:

```bash
pip install "iokit[ultra]"
```

Without it, a format tells you what it wants:

```python
from iokit import Yaml

Yaml({"key": "value"}, "single")
```

```plain-text
ModuleNotFoundError: Missing required packages: PyYAML>=6.0.1. Install with: pip install PyYAML
```

## Usage

Here are some examples of how to use the I/O Kit library:

### Text File Handling

```python
from iokit import Txt

text = "Hello, World!"
state = Txt(text, "text")
print(state)
print(state.load())
```

```plain-text
text.txt (13B)
Hello, World!
```

The first argument is the payload, the second the stem: the name with the extension left off. A whole path may be given instead, extension included.

```python
from iokit import Json

state = Json({"key": "value"}, path="reports/summary.json")
print(state.path, state.name, state.stem, state.suffix, state.size)
```

```plain-text
reports/summary.json summary.json summary .json 16
```

### JSON

```python
from iokit import Json

data = {"key": "value"}
state = Json(data, "single")
print(state)
print(state.load())
```

```plain-text
single.json (16B)
{'key': 'value'}
```

### YAML

```python
from iokit import Yaml

data = {"key": "value"}
state = Yaml(data, "single")
print(state)
print(state.load())
```

```plain-text
single.yaml (11B)
{'key': 'value'}
```

### GZip Compression

Compressing a state appends `.gz` to its path, and loading the result gives the original state back.

```python
from iokit import Txt

state = Txt("Hello, World! " * 1000, "data").gzip()
print(state)
print(len(state.load().load()))
```

```plain-text
data.txt.gz (133B)
14000
```

### Tar Archive

Archives load lazily, yielding their members one at a time.

```python
from iokit import Tar, Txt

state1 = Txt("First file", "text1")
state2 = Txt("Second file", "text2")
archive = Tar([state1, state2], "archive")
states = list(archive.load())
print(states)
print(states[0].load())
print(states[1].load())
```

```plain-text
[text1.txt (10B), text2.txt (11B)]
First file
Second file
```

### Finding States

`first` picks the one state matching a glob pattern, `filtrate` yields every match.

```python
from iokit import Tar, Txt, filtrate, first

state1 = Txt("First file", "text1")
state2 = Txt("Second file", "text2")
archive = Tar([state1, state2], "archive")

print(first(archive.load(), "?e*2.txt").load())
print([state.path for state in filtrate(archive.load(), "*.txt")])
```

```plain-text
Second file
['text1.txt', 'text2.txt']
```

### Byte input handling

`LoadedState` holds bytes already encoded, and the path decides how they are read.

```python
from iokit import LoadedState

state = LoadedState(b'{"first": 1, "second": 2}', path="data.json")
print(state)
print(state.load())
```

```plain-text
data.json (25B)
{'first': 1, 'second': 2}
```

### Files on Disk

`file` takes a path as a state, reading from it only when asked. Naming the expected format checks the extension and types the payload.

```python
from iokit import Txt, file

state = Txt("on disk", "note")
saved = state.save("/tmp/example", parents=True)
print(saved)
print(file(saved.path, Txt).load())
```

```plain-text
/tmp/example/note.txt (7B)
on disk
```

`save_temp` writes to a temporary directory that is removed on leaving the context.

```python
from iokit import Json

with Json({"key": "value"}, "config").save_temp() as saved:
    print(saved.name, saved.load())
```

```plain-text
config.json {'key': 'value'}
```

### Downloading

`web` fetches a url into a state, pathed after the url and timestamped after `Last-Modified` when the server sends it.

```python
from iokit import web

state = web("https://raw.githubusercontent.com/rilshok/iokit/main/LICENSE")
print(state.name)
print("MIT License" in state.data.decode("utf-8"))
```

```plain-text
LICENSE
True
```

Naming a format, as in `web(url, Json)`, checks the extension of the url and types the payload, the way `file` does.

### Encryption

Encrypting appends `.enc` to the path; the password is given again on loading.

```python
from iokit import Txt

secret = Txt("classified", "notes").encrypt(password="hunter2")
print(secret)
print(secret.load(password="hunter2").load())
```

```plain-text
notes.txt.enc (32B)
classified
```

### Checksums

```python
from iokit import Txt

state = Txt("Hello, World!", "text")
print(state.digest("sha256").base64)
print(state.digest("xxh128").base64url)
```

```plain-text
3/1gIbsr1bCvZ2KQgJ7DpTGR3YHH9wpLKGiKNiGCmG8=
Ux3yhERH3VB32wOELNdTlQ
```

## Contributing

Contributions to the IOkit library are welcome. Please feel free to submit a pull request or open an issue on the GitHub repository.

## License

The IOkit library is licensed under the MIT License. You can use it for commercial and non-commercial projects without any restrictions.
