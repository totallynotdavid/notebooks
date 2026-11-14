"""Keep a function's results on disk across builds of an article."""

from __future__ import annotations

import contextlib
import functools
import hashlib
import inspect
import pickle
from collections.abc import Callable, Iterator
from pathlib import Path

# Set only while quire runs an article; elsewhere a cached function just runs.
_directory: Path | None = None


@contextlib.contextmanager
def caching_in(directory: Path | None) -> Iterator[None]:
    global _directory
    previous, _directory = _directory, directory
    try:
        yield
    finally:
        _directory = previous


def cache[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    """The key is the function's source, the source of the module that defines
    it, and the pickled arguments. A change to a helper in another module is not
    seen: delete the cache folder, or build with --no-cache."""
    code = _source(function)

    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if _directory is None:
            return function(*args, **kwargs)
        digest = hashlib.sha256(code)
        digest.update(pickle.dumps((args, sorted(kwargs.items()))))
        path = _directory / f"{function.__qualname__}-{digest.hexdigest()[:16]}.pkl"
        if path.exists():
            return pickle.loads(path.read_bytes())
        result = function(*args, **kwargs)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".partial")
        partial.write_bytes(pickle.dumps(result))
        partial.replace(path)
        return result

    return wrapper


def _source(function: Callable) -> bytes:
    module = inspect.getmodule(function)
    module_file = getattr(module, "__file__", None)
    # A function defined in a fence has the article as its file; hash only its
    # own lines so editing prose elsewhere keeps the cache.
    if module_file and module_file.endswith(".py"):
        return Path(module_file).read_bytes()
    return inspect.getsource(function).encode()
