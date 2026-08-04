__all__ = ["CsvCodec", "TsvCodec"]

from io import BytesIO
from typing import BinaryIO

from pandas import DataFrame, read_csv

from iokit.codec.base import Codec


class _TableCodec(Codec[DataFrame]):
    __separator__: str

    def __init__(self, encoding: str = "utf-8", *, index: bool = False) -> None:
        self._encoding = encoding
        self._index = index

    def __repr__(self) -> str:
        return f"{type(self).__name__}(encoding={self._encoding}, index={self._index})"

    def encode(self, data: DataFrame) -> BytesIO:
        buffer = BytesIO()
        data.to_csv(buffer, sep=self.__separator__, index=self._index, encoding=self._encoding)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> DataFrame:
        with buffer:
            return read_csv(buffer, sep=self.__separator__, encoding=self._encoding)


class CsvCodec(_TableCodec):
    __separator__ = ","


class TsvCodec(_TableCodec):
    __separator__ = "\t"
