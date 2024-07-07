# I/O Kit Python Library

IOKit is a Python library that offers a suite of utilities for managing a wide range of input/output operations. Central to its design is the concept of a `State`, where each state signifies a unit of data that can be loaded, saved, or transformed. Each state corresponds to a valid file state, represented as a bytes-like object.

IOKit abstracts and unifies serialization and deserialization operations from various libraries into a single, cohesive interface. This allows for direct manipulation of the file's state in memory, eliminating the need for disk interaction. Consequently, it facilitates the (de)serialization of data in multiple formats, such as `json`, `yaml`, `txt`, `tar`, `gzip`, among others. This abstraction not only simplifies data handling but also enhances efficiency by reducing disk I/O operations.

## Installation

You can install the IOkit library using pip:

```bash
pip install iokit
```

## Usage

Here are some examples of how to use the I/O Kit library:

### Text File Handling

```python
from iokit import Txt

text = "Hello, World!"
state = Txt(text, name="text")
print(state)
print(state.load())
```

```plain-text
text.txt (13B)
Hello, World!
```

### JSON

```python
from iokit import Json

data = {"key": "value"}
state = Json(data, name="single")
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
state = Yaml(data, name="single")
print(state)
print(state.load())
```

```plain-text
single.yaml (11B)
{'key': 'value'}
```

### GZip Compression

```python
from iokit import Txt, Gzip

data = "Hello, World! "* 1000
state = Gzip(Txt(data, name="data"))
print(state)
print(len(state.load().load()))
```

```plain-text
data.txt.gz (133B)
14000
```

### Tar Archive

```python
from iokit import Tar, Txt

state1 = Txt("First file", name="text1")
state2 = Txt("Second file", name="text2")
archive = Tar([state1, state2], name="archive")
states = archive.load()
print(states)
print(states[0].load())
print(states[1].load())
```

```plain-text
[text1.txt (10B), text2.txt (11B)]
First file
Second file
```

### Find State

```python
from iokit import Tar, find_state

state1 = Txt("First file", name="text1")
state2 = Txt("Second file", name="text2")
archive = Tar([state1, state2], name="archive")

state = find_state(archive.load(), "?e*2.txt")
print(state.load())
```

```plain-text
Second file
```

### Byte input handling

```python
from iokit import State

state = State(b"{\"first\": 1, \"second\": 2}", name="data.json")
print(state.load())
```

```plain-text
{'first': 1, 'second': 2}
```


## Contributing

Contributions to the IOkit library are welcome. Please feel free to submit a pull request or open an issue on the GitHub repository.

## License

The IOkit library is licensed under the MIT License. You can use it for commercial and non-commercial projects without any restrictions.
