import importlib.metadata as md

from packaging.requirements import Requirement


def satisfies(req: str | Requirement) -> bool:
    if isinstance(req, str):
        req = Requirement(req)
    try:
        version = md.version(req.name)
    except md.PackageNotFoundError:
        return False
    return req.specifier.contains(version, prereleases=True)
