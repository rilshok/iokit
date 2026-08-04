from io import BytesIO
from typing import BinaryIO

from PIL import Image

from iokit.codec.base import Codec


class _PillowCodec(Codec[Image.Image]):
    __extension__: str

    def encode(self, data: Image.Image) -> BytesIO:
        buffer = BytesIO()
        data.save(buffer, format=self.__extension__)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> Image.Image:
        with buffer, Image.open(buffer) as image:
            image.load()
            return image


class AvifPillowCodec(_PillowCodec):
    __extension__ = "AVIF"


class BlpPillowCodec(_PillowCodec):
    __extension__ = "BLP"


class BmpPillowCodec(_PillowCodec):
    __extension__ = "BMP"


class BufrPillowCodec(_PillowCodec):
    __extension__ = "BUFR"


class CurPillowCodec(_PillowCodec):
    __extension__ = "CUR"


class DcxPillowCodec(_PillowCodec):
    __extension__ = "DCX"


class DdsPillowCodec(_PillowCodec):
    __extension__ = "DDS"


class DibPillowCodec(_PillowCodec):
    __extension__ = "DIB"


class EpsPillowCodec(_PillowCodec):
    __extension__ = "EPS"


class FitsPillowCodec(_PillowCodec):
    __extension__ = "FITS"


class FliPillowCodec(_PillowCodec):
    __extension__ = "FLI"


class FtexPillowCodec(_PillowCodec):
    __extension__ = "FTEX"


class GbrPillowCodec(_PillowCodec):
    __extension__ = "GBR"


class GifPillowCodec(_PillowCodec):
    __extension__ = "GIF"


class GribPillowCodec(_PillowCodec):
    __extension__ = "GRIB"


class Hdf5PillowCodec(_PillowCodec):
    __extension__ = "HDF5"


class IcnsPillowCodec(_PillowCodec):
    __extension__ = "ICNS"


class IcoPillowCodec(_PillowCodec):
    __extension__ = "ICO"


class ImPillowCodec(_PillowCodec):
    __extension__ = "IM"


class IptcPillowCodec(_PillowCodec):
    __extension__ = "IPTC"


class JpegPillowCodec(_PillowCodec):
    __extension__ = "JPEG"


class Jpeg2000PillowCodec(_PillowCodec):
    __extension__ = "JPEG2000"


class MpegPillowCodec(_PillowCodec):
    __extension__ = "MPEG"


class MpoPillowCodec(_PillowCodec):
    __extension__ = "MPO"


class MspPillowCodec(_PillowCodec):
    __extension__ = "MSP"


class PalmPillowCodec(_PillowCodec):
    __extension__ = "PALM"


class PcdPillowCodec(_PillowCodec):
    __extension__ = "PCD"


class PcxPillowCodec(_PillowCodec):
    __extension__ = "PCX"


class PdfPillowCodec(_PillowCodec):
    __extension__ = "PDF"


class PixarPillowCodec(_PillowCodec):
    __extension__ = "PIXAR"


class PngPillowCodec(_PillowCodec):
    __extension__ = "PNG"


class PpmPillowCodec(_PillowCodec):
    __extension__ = "PPM"


class PsdPillowCodec(_PillowCodec):
    __extension__ = "PSD"


class QoiPillowCodec(_PillowCodec):
    __extension__ = "QOI"


class SgiPillowCodec(_PillowCodec):
    __extension__ = "SGI"


class SunPillowCodec(_PillowCodec):
    __extension__ = "SUN"


class TgaPillowCodec(_PillowCodec):
    __extension__ = "TGA"


class TiffPillowCodec(_PillowCodec):
    __extension__ = "TIFF"


class WebpPillowCodec(_PillowCodec):
    __extension__ = "WEBP"


class WmfPillowCodec(_PillowCodec):
    __extension__ = "WMF"


class XbmPillowCodec(_PillowCodec):
    __extension__ = "XBM"


class XpmPillowCodec(_PillowCodec):
    __extension__ = "XPM"
