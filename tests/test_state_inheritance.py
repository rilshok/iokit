from iokit import Json, State


class MyJson(Json, suffix="myjson"):
    pass


def test_state_inheritance_json() -> None:
    assert getattr(MyJson, "_suffix") == "myjson"
    assert getattr(MyJson, "_suffixes") == ("myjson",)
    myjson = MyJson({"a": 1}, name="test")
    assert myjson.name == "test.myjson"
    loaded = State(data=myjson.data, name="test.myjson")
    assert loaded.load() == myjson.load() == {"a": 1}
