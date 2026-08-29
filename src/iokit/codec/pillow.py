"""Codecs for image formats using Pillow."""

from io import BytesIO
from typing import BinaryIO

from PIL import Image

from iokit.codec.base import Codec


class _PillowCodec(Codec[Image.Image]):
    """Base codec for image formats using Pillow."""

    __extension__: str

    def __repr__(self) -> str:
        """Return codec representation."""
        return f"{type(self).__name__}()"

    def encode(self, data: Image.Image) -> BytesIO:
        """Save `data` to the format specified by the subclass extension."""
        buffer = BytesIO()
        data.save(buffer, format=self.__extension__)
        buffer.seek(0)
        return buffer

    def decode(self, buffer: BinaryIO) -> Image.Image:
        """Load an image from `buffer`, materializing it immediately."""
        with buffer, Image.open(buffer) as image:
            image.load()
            return image


class AvifPillowCodec(_PillowCodec):
    """Codec for AVIF images using Pillow."""

    __extension__ = "AVIF"


class BlpPillowCodec(_PillowCodec):
    """Codec for BLP images using Pillow."""

    __extension__ = "BLP"


class BmpPillowCodec(_PillowCodec):
    """Codec for BMP images using Pillow."""

    __extension__ = "BMP"


class BufrPillowCodec(_PillowCodec):
    """Codec for BUFR images using Pillow."""

    __extension__ = "BUFR"


class CurPillowCodec(_PillowCodec):
    """Codec for CUR images using Pillow."""

    __extension__ = "CUR"


class DcxPillowCodec(_PillowCodec):
    """Codec for DCX images using Pillow."""

    __extension__ = "DCX"


class DdsPillowCodec(_PillowCodec):
    """Codec for DDS images using Pillow."""

    __extension__ = "DDS"


class DibPillowCodec(_PillowCodec):
    """Codec for DIB images using Pillow."""

    __extension__ = "DIB"


class EpsPillowCodec(_PillowCodec):
    """Codec for EPS images using Pillow."""

    __extension__ = "EPS"


class FitsPillowCodec(_PillowCodec):
    """Codec for FITS images using Pillow."""

    __extension__ = "FITS"


class FliPillowCodec(_PillowCodec):
    """Codec for FLI images using Pillow."""

    __extension__ = "FLI"


class FtexPillowCodec(_PillowCodec):
    """Codec for FTEX images using Pillow."""

    __extension__ = "FTEX"


class GbrPillowCodec(_PillowCodec):
    """Codec for GBR images using Pillow."""

    __extension__ = "GBR"


class GifPillowCodec(_PillowCodec):
    """Codec for GIF images using Pillow."""

    __extension__ = "GIF"


class GribPillowCodec(_PillowCodec):
    """Codec for GRIB images using Pillow."""

    __extension__ = "GRIB"


class Hdf5PillowCodec(_PillowCodec):
    """Codec for HDF5 images using Pillow."""

    __extension__ = "HDF5"


class IcnsPillowCodec(_PillowCodec):
    """Codec for ICNS images using Pillow."""

    __extension__ = "ICNS"


class IcoPillowCodec(_PillowCodec):
    """Codec for ICO images using Pillow."""

    __extension__ = "ICO"


class ImPillowCodec(_PillowCodec):
    """Codec for IM images using Pillow."""

    __extension__ = "IM"


class IptcPillowCodec(_PillowCodec):
    """Codec for IPTC images using Pillow."""

    __extension__ = "IPTC"


class JpegPillowCodec(_PillowCodec):
    """Codec for JPEG images using Pillow."""

    __extension__ = "JPEG"


class Jpeg2000PillowCodec(_PillowCodec):
    """Codec for JPEG2000 images using Pillow."""

    __extension__ = "JPEG2000"


class MpegPillowCodec(_PillowCodec):
    """Codec for MPEG images using Pillow."""

    __extension__ = "MPEG"


class MpoPillowCodec(_PillowCodec):
    """Codec for MPO images using Pillow."""

    __extension__ = "MPO"


class MspPillowCodec(_PillowCodec):
    """Codec for MSP images using Pillow."""

    __extension__ = "MSP"


class PalmPillowCodec(_PillowCodec):
    """Codec for PALM images using Pillow."""

    __extension__ = "PALM"


class PcdPillowCodec(_PillowCodec):
    """Codec for PCD images using Pillow."""

    __extension__ = "PCD"


class PcxPillowCodec(_PillowCodec):
    """Codec for PCX images using Pillow."""

    __extension__ = "PCX"


class PdfPillowCodec(_PillowCodec):
    """Codec for PDF images using Pillow."""

    __extension__ = "PDF"


class PixarPillowCodec(_PillowCodec):
    """Codec for Pixar images using Pillow."""

    __extension__ = "PIXAR"


class PngPillowCodec(_PillowCodec):
    """Codec for PNG images using Pillow."""

    __extension__ = "PNG"


class PpmPillowCodec(_PillowCodec):
    """Codec for PPM images using Pillow."""

    __extension__ = "PPM"


class PsdPillowCodec(_PillowCodec):
    """Codec for PSD images using Pillow."""

    __extension__ = "PSD"


class QoiPillowCodec(_PillowCodec):
    """Codec for QOI images using Pillow."""

    __extension__ = "QOI"


class SgiPillowCodec(_PillowCodec):
    """Codec for SGI images using Pillow."""

    __extension__ = "SGI"


class SunPillowCodec(_PillowCodec):
    """Codec for Sun images using Pillow."""

    __extension__ = "SUN"


class TgaPillowCodec(_PillowCodec):
    """Codec for TGA images using Pillow."""

    __extension__ = "TGA"


class TiffPillowCodec(_PillowCodec):
    """Codec for TIFF images using Pillow."""

    __extension__ = "TIFF"


class WebpPillowCodec(_PillowCodec):
    """Codec for WebP images using Pillow."""

    __extension__ = "WEBP"


class WmfPillowCodec(_PillowCodec):
    """Codec for WMF images using Pillow."""

    __extension__ = "WMF"


class XbmPillowCodec(_PillowCodec):
    """Codec for XBM images using Pillow."""

    __extension__ = "XBM"


class XpmPillowCodec(_PillowCodec):
    """Codec for XPM images using Pillow."""

    __extension__ = "XPM"
