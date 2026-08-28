import pytest

from iokit import Json

DOCUMENT = {"key": "value"}
PASSWORD = "pA$sw0Rd"  # noqa: S105
SALT = "s@lt"


def test_an_encrypted_state_is_read_back_by_the_password_it_was_written_with() -> None:
    state = Json(DOCUMENT, path="document.json").encrypt(password=PASSWORD, salt=SALT)
    assert state.path == "document.json.enc"
    decrypted = state.load(password=PASSWORD, salt=SALT)
    assert decrypted.name == "document.json"
    assert decrypted.load() == DOCUMENT


@pytest.mark.parametrize(
    ("password", "salt"),
    [(PASSWORD, ""), ("password", SALT), ("password", "")],
)
def test_neither_a_wrong_password_nor_a_wrong_salt_opens_a_state(
    password: str,
    salt: str,
) -> None:
    state = Json(DOCUMENT, path="document.json").encrypt(password=PASSWORD, salt=SALT)
    with pytest.raises(ValueError, match="Decryption failed"):
        state.load(password=password, salt=salt)
