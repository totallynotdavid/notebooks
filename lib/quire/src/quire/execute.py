"""Run an article's Python fences top to bottom in one namespace."""

from __future__ import annotations

import ast
import contextlib
import io
import os
import sys
import traceback
from pathlib import Path

from quire.cache import caching_in
from quire.document import Code, Prose, parse
from quire.outputs import to_output
from quire.parameter import collecting

VERSION = 1
CACHE_DIR = ".quire-cache"


class ArticleError(Exception):
    """A fence raised; the message is the traceback against article lines."""


def run_article(path: Path, *, use_cache: bool = True) -> dict:
    with collecting() as registry:
        blocks, _ = _execute(path, use_cache)
    return {"version": VERSION, "blocks": blocks} | registry.export()


def article_namespace(path: Path, *, use_cache: bool = True) -> dict:
    """The names an article defines after its last fence, for tests."""
    with collecting():
        _, namespace = _execute(path, use_cache)
    return namespace


def _execute(path: Path, use_cache: bool) -> tuple[list[dict], dict]:
    path = path.resolve()
    blocks = parse(path.read_text(encoding="utf-8"))
    namespace: dict[str, object] = {"__name__": "__quire__", "__file__": str(path)}
    rendered: list[dict] = []
    cache_dir = path.parent / CACHE_DIR if use_cache else None
    with _article_context(path.parent), caching_in(cache_dir, path.parent):
        for block in blocks:
            if isinstance(block, Prose):
                rendered.append({"type": "prose", "text": block.text})
                continue
            outputs = _run_fence(block, path, namespace)
            if block.hidden and not outputs:
                continue
            rendered.append(
                {
                    "type": "code",
                    "source": block.source,
                    "hidden": block.hidden,
                    "outputs": outputs,
                }
            )
    return rendered, namespace


@contextlib.contextmanager
def _article_context(directory: Path):
    """Imports and relative paths resolve against the article's folder."""
    previous = Path.cwd()
    sys.path.insert(0, str(directory))
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(previous)
        sys.path.remove(str(directory))


def _run_fence(block: Code, path: Path, namespace: dict) -> list[dict]:
    tree = ast.parse(block.source, filename=str(path))
    # Line numbers in tracebacks then point into the article itself.
    ast.increment_lineno(tree, block.line - 1)
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body.pop().value)

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(compile(tree, str(path), "exec"), namespace)
            value = eval(compile(last, str(path), "eval"), namespace) if last else None
    except Exception as error:
        raise ArticleError("".join(traceback.format_exception(error))) from error

    outputs: list[dict] = []
    if stdout.getvalue():
        outputs.append({"type": "stdout", "text": stdout.getvalue()})
    output = to_output(value)
    if output is not None:
        outputs.append(output)
    return outputs
