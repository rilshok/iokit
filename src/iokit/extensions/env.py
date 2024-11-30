__all__ = ["Env"]

from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import dotenv

from iokit.state import State, StateName


class Env(State, suffix="env"):
    def __init__(
        self,
        data: dict[str, str],
        /,
        name: str | StateName = "",
        *,
        time: datetime | None = None,
    ) -> None:
        with TemporaryDirectory() as root:
            path = Path(root) / "env"
            for key, value in data.items():
                dotenv.set_key(
                    dotenv_path=path,
                    key_to_set=key,
                    value_to_set=value,
                    quote_mode="auto",
                )
            super().__init__(path.read_bytes(), name=name, time=time)

    def load(self) -> dict[str, str | None]:
        with StringIO(self.data.decode()) as stream:
            return dict(dotenv.dotenv_values(stream=stream))
