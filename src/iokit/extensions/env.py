from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import dotenv

from iokit.state import State


class Env(State, suffix="env"):
    def __init__(self, data: dict[str, str], **kwargs: Any):
        with TemporaryDirectory() as root:
            path = Path(root) / "env"
            for key, value in data.items():
                dotenv.set_key(
                    dotenv_path=path, key_to_set=key, value_to_set=value, quote_mode="auto"
                )
            data_bytes = path.read_bytes()
        super().__init__(data=data_bytes, **kwargs)

    def load(self) -> dict[str, str | None]:
        stream = StringIO(self.data.getvalue().decode())
        return dict(dotenv.dotenv_values(stream=stream))
