"""`quire build` writes an article's document; `quire watch` rebuilds on save."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from quire.execute import ArticleError, run_article


def build(article: Path, output: Path) -> None:
    document = run_article(article)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Write then rename, so a dev server never reads half a document.
    partial = output.with_suffix(".partial")
    partial.write_text(
        json.dumps(document, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    partial.replace(output)
    print(f"{article} -> {output} ({output.stat().st_size:,} bytes)")


def watch(article: Path, output: Path) -> None:
    """Rebuild in a fresh process whenever the article or a sibling module
    changes, so edited modules are imported again."""
    command = [sys.executable, "-m", "quire", "build", str(article), "-o", str(output)]
    seen: dict[Path, float] = {}
    while True:
        current = {
            p: p.stat().st_mtime
            for p in [article, *article.parent.glob("**/*.py")]
            if "__pycache__" not in p.parts
        }
        if current != seen:
            seen = current
            subprocess.run(command, check=False)
        time.sleep(0.5)


def main() -> int:
    parser = argparse.ArgumentParser(prog="quire", description=__doc__)
    parser.add_argument("command", choices=["build", "watch"])
    parser.add_argument("article", type=Path, help="Markdown article to run")
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "watch":
        try:
            watch(args.article, args.output.resolve())
        except KeyboardInterrupt:
            return 0
    try:
        build(args.article, args.output.resolve())
    except (ArticleError, SyntaxError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0
