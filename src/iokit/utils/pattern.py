"""Pattern matching utilities."""

from fnmatch import fnmatch


class Pattern(str):
    """A string pattern for matching filenames using wildcards.

    Patterns support * for any sequence of characters.
    The length is computed without wildcards.
    """

    __slots__ = ()

    def __len__(self) -> int:
        """Get the length of the pattern without wildcards.

        Returns:
            The length of the pattern string with * characters removed.

        """
        return len(self.replace("*", ""))

    def __call__(self, string: str) -> bool:
        """Test if a string matches this pattern.

        Args:
            string: The string to match against the pattern.

        Returns:
            Whether the string matches the pattern.

        """
        return fnmatch(name=string, pat=str(self))
