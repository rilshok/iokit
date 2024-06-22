import tarfile
from io import BytesIO
from typing import Any, Iterable

from iokit.state import State
from iokit.tools.time import fromtimestamp


class Tar(State, suffix="tar"):
    def __init__(self, states: Iterable[State], **kwargs: Any):
        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar_buffer:
            for state in states:
                file_data = tarfile.TarInfo(name=str(state.name))
                file_data.size = state.size
                file_data.mtime = int(state.time.timestamp())
                tar_buffer.addfile(fileobj=state.data, tarinfo=file_data)

        super().__init__(data=buffer, **kwargs)

    def load(self) -> list[State]:
        states: list[State] = []
        with tarfile.open(fileobj=self.data, mode="r") as tar_buffer:
            assert tar_buffer is not None
            for member in tar_buffer.getmembers():
                if not member.isfile():
                    continue
                member_buffer = tar_buffer.extractfile(member)
                if member_buffer is None:
                    continue
                state = State(
                    data=member_buffer.read(),
                    name=member.name,
                    time=fromtimestamp(member.mtime),
                )
                states.append(state)
        return states
