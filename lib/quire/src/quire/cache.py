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
_modules = b""


def module_files(folder: Path) -> list[Path]:
    """The Python files an article in `folder` can import; tests are not."""
    return sorted(
        path
        for path in folder.glob("**/*.py")
        if not {"__pycache__", "tests"} & set(path.relative_to(folder).parts)
    )


@contextlib.contextmanager
def caching_in(directory: Path | None, folder: Path) -> Iterator[None]:
    """Store results in `directory`, keyed also by the modules in `folder`."""
    global _directory, _modules
    previous = _directory, _modules
    digest = hashlib.sha256()
    for path in module_files(folder):
        digest.update(str(path.relative_to(folder)).encode())
        digest.update(path.read_bytes())
    _directory, _modules = directory, digest.digest()
    try:
        yield
    finally:
        _directory, _modules = previous


def cache[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    """The key is the function's own source, every module beside the article,
    and the pickled arguments. Globals the function reads are not part of it."""
    code = inspect.getsource(function).encode()

    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if _directory is None:
            return function(*args, **kwargs)
        digest = hashlib.sha256(code)
        digest.update(_modules)
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
