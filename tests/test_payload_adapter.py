"""A format subclassed to carry a payload of its own, through `dump` and `parse`.

The file stays an ordinary one of its format; only the two ends of the trip belong to the user.
"""

from dataclasses import asdict, dataclass
from typing import Any

import pytest
from typing_extensions import TypeVar

from iokit import Expected, Json, LoadedState, MemoryStorage, StateStorage, Txt


@dataclass
class Person:
    name: str
    age: int


@dataclass
class Employee(Person):
    title: str


JOE = Person("Joe", 32)
BOSS = Employee("Joe", 32, "boss")
DOCUMENT: dict[str, Any] = {"name": "Joe", "age": 32}
TOUCHED = 1_700_000_000.0


class PersonJson(Json[Person]):
    """A person filed as a JSON object of the two fields they are."""

    __expected__ = dict

    def dump(self, data: Person) -> dict[str, Any]:
        return {"name": data.name, "age": data.age}

    def parse(self, data: dict[str, Any]) -> Person:
        return Person(data["name"], data["age"])


class PersonTxt(Txt[Person]):
    """The same person on a line of text, since the trick is not the JSON's."""

    def dump(self, data: Person) -> str:
        return f"{data.name},{data.age}"

    def parse(self, data: str) -> Person:
        name, age = data.rsplit(",", 1)
        return Person(name, int(age))


class StemJson(PersonJson):
    """A person named after the state, over what the class above already writes."""

    def dump(self, data: Person) -> dict[str, Any]:
        return {**super().dump(data), "name": self.stem}


PersonT = TypeVar("PersonT", bound=Person, default=Person)


class AnyPersonJson(Json[PersonT]):
    """A person of whichever kind the class below names."""

    # annotated, so a class below may expect something else of the codec than this one does
    __expected__: Expected = dict
    __person__: type[PersonT]

    def dump(self, data: PersonT) -> dict[str, Any]:
        return asdict(data)

    def parse(self, data: dict[str, Any]) -> PersonT:
        return self.__person__(**data)


class EmployeeJson(AnyPersonJson[Employee]):
    """The payload named, and nothing else to say."""

    __person__ = Employee


class EitherJson(AnyPersonJson[Person]):
    """A person read from a document, or from a bare pair of fields."""

    # wider than the `dict` above: whatever the codec read, `parse` sorts it out
    __expected__: Expected = object
    __person__ = Person

    def parse(self, data: dict[str, Any] | list[Any]) -> Person:
        if isinstance(data, list):
            return Person(*data)
        return super().parse(data)


def test_round_trip() -> None:
    state = PersonJson(JOE, "joe")
    assert state.path == "joe.json"
    assert state.data == Json(DOCUMENT).data
    assert state.load() == JOE


def test_reads_as_a_plain_document() -> None:
    """The bytes are the format's own, so a state without the adapter reads them, and it theirs."""
    assert Json.from_state(PersonJson(JOE, "joe")).load() == DOCUMENT
    assert PersonJson.from_state(Json(DOCUMENT, "joe")).load() == JOE


def test_expected_guards_parse() -> None:
    """A document `parse` was not written for is turned away before it gets there."""
    state = PersonJson.from_state(LoadedState(Json([DOCUMENT]).data, path="joe.json"))
    with pytest.raises(TypeError, match="Expected loaded data of type 'dict'"):
        state.load()


def test_another_format() -> None:
    state = PersonTxt(JOE, "joe")
    assert state.path == "joe.txt"
    assert state.data == b"Joe,32"
    assert state.load() == JOE


def test_through_a_storage() -> None:
    backend = MemoryStorage()
    backend.push("joe.json", PersonJson(JOE, "joe").data)
    assert StateStorage(backend).pull_state("joe.json", PersonJson).load() == JOE


def test_dump_over_the_pair_above() -> None:
    """`super()` reaches the `dump` above, and by then `self` is a state that knows its name."""
    state = StemJson(Person("", 32), "joe", timestamp=TOUCHED)
    assert state.data == Json({"name": "joe", "age": 32}).data
    assert state.load() == Person("joe", 32)
    assert state.timestamp == TOUCHED


def test_payload_named_by_the_subclass() -> None:
    assert EmployeeJson(BOSS, "joe").load() == BOSS
    assert Json.from_state(EmployeeJson(BOSS, "joe")).load() == asdict(BOSS)


def test_expected_widened_below() -> None:
    assert EitherJson.from_state(Json(["Joe", 32], "joe")).load() == JOE
    assert EitherJson.from_state(Json(DOCUMENT, "joe")).load() == JOE
