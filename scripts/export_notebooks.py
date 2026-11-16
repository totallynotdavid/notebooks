from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from notebooks_manifest import (
    ROOT,
    SITE_DIR,
    Notebook,
    frontend_data_is_current,
    load_manifest,
    validate_manifest,
    write_frontend_data,
)

TMP_ROOT = Path(tempfile.gettempdir()).resolve()
# The site's article route reads these documents at prerender time.
ARTICLES_DIR = SITE_DIR / ".articles"


def run(command: list[str]) -> int:
    print("+ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def clean_output_dir(output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    if not output_dir.exists():
        return

    inside_repo = ROOT in output_dir.parents
    inside_tmp = TMP_ROOT in output_dir.parents
    if not inside_repo and not inside_tmp:
        raise SystemExit(
            f"Refusing to clean a path outside the repository: {output_dir}"
        )
    if output_dir in {ROOT, TMP_ROOT, SITE_DIR.resolve()}:
        raise SystemExit(f"Refusing to clean root directory: {output_dir}")

    shutil.rmtree(output_dir)


def build_article(notebook: Notebook, output_dir: Path) -> None:
    """Run an article in its package and write its document for the site.

    `quire build` exits non-zero when a fence raises, which fails the build.
    """
    output = output_dir / f"{notebook.slug}.json"
    command = ["uv", "run", "--locked", "--package", notebook.package, "quire"]
    if run([*command, "build", notebook.path, "-o", str(output)]):
        raise SystemExit(f"Build failed for {notebook.path}")


def export_notebooks(clean: bool) -> None:
    _, notebooks = load_manifest()
    validate_manifest(notebooks)

    if clean:
        clean_output_dir(ARTICLES_DIR)
    for notebook in notebooks:
        build_article(notebook, ARTICLES_DIR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the catalog and build the published articles."
    )
    parser.add_argument(
        "command",
        choices=["validate", "data", "export"],
        help="Action to run.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove built articles before building.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="With data, fail when the generated catalog is out of date "
        "instead of writing it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    site, notebooks = load_manifest()
    validate_manifest(notebooks)

    if args.command == "validate":
        return 0
    if args.command == "data":
        if not args.check:
            write_frontend_data(site, notebooks)
        elif not frontend_data_is_current(site, notebooks):
            raise SystemExit(
                "site/src/lib/catalog.generated.ts is out of date. Run `mise run data`."
            )
        return 0
    if args.command == "export":
        export_notebooks(args.clean)
        return 0

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
