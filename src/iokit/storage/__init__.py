__all__ = [
    "load_file",
    "save_file",
    "save_temp",
    "download_file",
]

from .local import load_file, save_file, save_temp
from .web import download_file
