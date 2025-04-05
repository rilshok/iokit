from datetime import datetime
from io import BytesIO

from PIL import Image

from iokit.state import State, StateName


class ImageState(State, suffix=""):
    def __init__(
        self,
        data: Image.Image,
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            data.save(buffer, format=self._suffix)
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> Image.Image:
        return Image.open(self.buffer)


class Jpeg(ImageState, suffix="jpeg", suffixes=("jpeg", "jpg")):
    pass


class Png(ImageState, suffix="png"):
    pass
