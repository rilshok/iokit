"""Dependency version checking utilities."""

import importlib.metadata as md

from packaging.requirements import Requirement


def satisfies(req: str | Requirement) -> bool:
    """Check if an installed package satisfies a version requirement.

    Args:
        req: A requirement specification as a string or Requirement object.

    Returns:
        Whether the installed version of the package satisfies the requirement.

    """
    if isinstance(req, str):
        req = Requirement(req)
    try:
        version = md.version(req.name)
    except md.PackageNotFoundError:
        return False
    return req.specifier.contains(version, prereleases=True)
