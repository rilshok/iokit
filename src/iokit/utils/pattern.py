from fnmatch import fnmatch


class Pattern(str):
    __slots__ = ()

    def __len__(self) -> int:
        return len(self.replace("*", ""))

    def __call__(self, string: str) -> bool:
        return fnmatch(name=string, pat=str(self))
