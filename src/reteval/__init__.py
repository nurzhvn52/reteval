"""reteval: reproducible evaluation of ranked retrieval runs."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("reteval")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0"

__all__ = ["__version__"]
