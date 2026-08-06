from iokit import Env


def test_env_state() -> None:
    data: dict[str, str | None] = {"login": "user", "password": "pass"}
    state = Env(data, stem="creds")
    assert state.size > 0
    assert state.name == "creds.env"
    assert state.load() == data
