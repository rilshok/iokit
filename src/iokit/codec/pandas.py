"""Codecs for tabular data (CSV and TSV)."""

__all__ = ["CsvCodec", "TsvCodec"]

from io import BytesIO
from typing import BinaryIO

from pandas import DataFrame, read_csv

from iokit.codec.base import Codec


class _TableCodec(Codec[DataFrame]):
    """Base codec for delimited tabular formats."""

    __separator__: str

    def __init__(self, encoding: str = "utf-8", *, index: bool = False) -> None:
        """Initialize codec with character encoding and index control.

        Args:
            encoding: Character encoding for the file.
            index: Write row labels as the first column.

        """
        self._encoding = encoding
        self._index = index

    def __repr__(self) -> str:
        """Return codec representation."""
        return f"{type(self).__name__}(encoding={self._encoding}, index={self._index})"

    def encode(self, data: DataFrame) -> BytesIO:
        """Serialize `data` to the delimited format defined by the subclass."""
        buffer = BytesIO()
        data.to_csv(buffer, sep=self.__separator__, index=self._index, encoding=self._encoding)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> DataFrame:
        """Parse delimited format from `buffer` into a DataFrame."""
        with buffer:
            return read_csv(buffer, sep=self.__separator__, encoding=self._encoding)


class CsvCodec(_TableCodec):
    """Convert between DataFrames and comma-separated values."""

    __separator__ = ","


class TsvCodec(_TableCodec):
    """Convert between DataFrames and tab-separated values."""

    __separator__ = "\t"
