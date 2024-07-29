from iokit import Env


def test_env_state() -> None:
    data = {"login": "user", "password": "pass"}
    state = Env(data, name="creds")
    assert state.size > 0
    assert state.name == "creds.env"
    assert state.load() == data
