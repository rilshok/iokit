"""Records kept as files under a root directory, which a uid may not lead out of.

The contract every storage keeps is in `tests/test_storage_contract.py`.
"""

from pathlib import Path

import pytest

from iokit import LocalStorage


def test_record_is_a_file(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    storage.push("reports/first.bin", b"hello")
    assert (tmp_path / "reports/first.bin").read_bytes() == b"hello"


def test_only_files_are_records(tmp_path: Path) -> None:
    """A directory of the root names no record, so the walk passes it by."""
    storage = LocalStorage(tmp_path)
    (tmp_path / "empty").mkdir()
    storage.push("reports/first.bin", b"hello")
    assert list(storage.index()) == ["reports/first.bin"]


def test_uid_out_of_the_root_refused(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path / "root")
    with pytest.raises(ValueError, match="is not a relative path naming a record"):
        storage.push("../escaped.bin", b"hello")
    assert not (tmp_path / "escaped.bin").exists()


def test_symlink_out_of_the_root_refused(tmp_path: Path) -> None:
    """A path that stays under the root as written, but not on disk, is refused all the same."""
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "away").symlink_to(outside, target_is_directory=True)
    storage = LocalStorage(root)
    with pytest.raises(ValueError, match="outside of the storage root"):
        storage.push("away/escaped.bin", b"hello")
    assert not (outside / "escaped.bin").exists()
