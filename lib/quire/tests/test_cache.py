"""When a cached function in an article runs again."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ARTICLE = """\
```python
from quire import cache
import helper

@cache
def scaled(n):
    with open("runs.log", "a") as log:
        log.write("ran\\n")
    return n * helper.factor()

scaled(3)
```
"""


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        (self.folder / "article.md").write_text(ARTICLE)
        self.set_factor(2)

    def set_factor(self, factor: int):
        (self.folder / "helper.py").write_text(f"def factor():\n    return {factor}\n")

    def build(self) -> int:
        """Build in a new process, as `quire build` and `quire watch` do."""
        output = self.folder / "article.json"
        # -B: helper.py is rewritten within the same second at the same size,
        # which a .pyc check (mtime in seconds, size) cannot tell apart.
        command = [sys.executable, "-B", "-m", "quire", "build", "article.md"]
        subprocess.run(
            [*command, "-o", output],
            cwd=self.folder,
            check=True,
            capture_output=True,
        )
        [block] = json.loads(output.read_text())["blocks"]
        return int(block["outputs"][0]["text"])

    def runs(self) -> int:
        return len((self.folder / "runs.log").read_text().splitlines())

    def test_a_second_build_reads_the_stored_result(self):
        self.build()
        self.build()
        self.assertEqual(self.runs(), 1)

    def test_editing_an_imported_module_runs_the_function_again(self):
        self.assertEqual(self.build(), 6)
        self.set_factor(5)
        self.assertEqual(self.build(), 15)

    def test_editing_a_test_file_keeps_the_stored_result(self):
        self.build()
        (self.folder / "tests").mkdir()
        (self.folder / "tests" / "test_helper.py").write_text("x = 1\n")
        self.build()
        self.assertEqual(self.runs(), 1)


if __name__ == "__main__":
    unittest.main()
