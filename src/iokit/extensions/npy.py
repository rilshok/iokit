__all__ = ["Npy"]

from datetime import datetime
from io import BytesIO
from typing import Any

import numpy as np
from numpy.typing import NDArray

from iokit.state import State, StateName


class Npy(State, suffix="npy"):
    def __init__(
        self,
        data: NDArray[Any],
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        with BytesIO() as buffer:
            np.save(buffer, data, allow_pickle=False)
            super().__init__(buffer.getvalue(), name=name, time=time)

    def load(self) -> NDArray[Any]:
        return np.load(self.buffer, allow_pickle=False)
