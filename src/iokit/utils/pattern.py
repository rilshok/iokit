from fnmatch import fnmatch

WRAPPER_PREFIX = "*.*"


class Pattern(str):
    def __len__(self) -> int:
        return len(self.replace("*", ""))

    def __call__(self, string: str) -> bool:
        return fnmatch(name=string, pat=str(self))

    @property
    def wrapper(self) -> bool:
        """Whether the pattern, like `*.*.gz`, describes a container around another format."""
        return self.startswith(WRAPPER_PREFIX)

    def unwrap(self, name: str) -> str:
        """Strip the container suffix, leaving the name of whatever the container holds."""
        return name.removesuffix(self.removeprefix(WRAPPER_PREFIX))
