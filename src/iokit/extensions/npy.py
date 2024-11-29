from io import BytesIO
from typing import Any

import numpy as np
from numpy.typing import NDArray

from iokit.state import State


class Npy(State, suffix="npy"):
    def __init__(self, array: NDArray[Any], **kwargs: Any) -> None:
        with BytesIO() as buffer:
            np.save(buffer, array, allow_pickle=False, fix_imports=False)
            super().__init__(data=buffer.getvalue(), **kwargs)

    def load(self) -> NDArray[Any]:
        return np.load(self.buffer, allow_pickle=False, fix_imports=False)
