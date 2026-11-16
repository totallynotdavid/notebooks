from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import export_notebooks
import notebooks_manifest
from notebooks_manifest import Notebook

FAILING_ARTICLE = """\
# Prueba

```python
raise ValueError("boom")
```
"""


def catalog_entry(path: str) -> Notebook:
    return Notebook(
        topic_id="numerical-methods",
        topic="Fundamentos numericos",
        title="Titulo de prueba",
        summary="Resumen de prueba",
        path=path,
        package_dir="packages/numerical-methods",
        slug="numerical-methods/prueba",
    )


class BuildArticleTest(unittest.TestCase):
    def test_a_failing_fence_fails_the_build_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            article = root / "prueba.md"
            article.write_text(FAILING_ARTICLE, encoding="utf-8")
            output = root / "out"

            with self.assertRaises(SystemExit):
                export_notebooks.build_article(catalog_entry(str(article)), output)

            self.assertFalse((output / "numerical-methods/prueba.json").exists())


class ValidateManifestTest(unittest.TestCase):
    def test_a_python_file_in_the_catalog_is_rejected(self):
        notebook = catalog_entry("packages/numerical-methods/raices.py")

        with self.assertRaises(SystemExit) as raised:
            notebooks_manifest.validate_manifest([notebook])

        self.assertIn("Not a Markdown article", str(raised.exception))


class CatalogDataTest(unittest.TestCase):
    def run_data(self, generated: Path, *flags: str) -> int:
        argv = ["export_notebooks.py", "data", *flags]
        with (
            mock.patch.object(notebooks_manifest, "GENERATED_DATA", generated),
            mock.patch.object(sys, "argv", argv),
        ):
            return export_notebooks.main()

    def test_check_fails_on_a_stale_catalog_without_writing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "catalog.generated.ts"
            generated.write_text("stale", encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                self.run_data(generated, "--check")

            self.assertIn("mise run data", str(raised.exception))
            self.assertEqual(generated.read_text(encoding="utf-8"), "stale")

    def test_check_passes_on_the_catalog_that_data_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "catalog.generated.ts"
            self.run_data(generated)
            written = generated.read_text(encoding="utf-8")

            self.assertEqual(self.run_data(generated, "--check"), 0)
            self.assertEqual(generated.read_text(encoding="utf-8"), written)


if __name__ == "__main__":
    unittest.main()
