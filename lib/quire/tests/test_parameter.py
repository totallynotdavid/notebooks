"""What an article that formats a parameter writes for the page."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from quire import parameter
from quire.execute import ArticleError, run_article

ARTICLE = """\
```python
from quire import md, parameter, plot as P

n = parameter("n", [2, 4, 8], value=4, format="{} nodos")
md(f"Con $n = {n:d}$ hay {n}, {n.each(lambda k: k * k)} y {n.each(lambda k: k * k)}.")
```

```python
P.figure(P.line(x=[0, 1], y=[0, 1]), frames=n)
```
"""


def build(source: str) -> dict:
    folder = Path(tempfile.mkdtemp())
    (folder / "article.md").write_text(source)
    return run_article(folder / "article.md", use_cache=False)


class ArticleParameterTest(unittest.TestCase):
    def test_an_article_exports_its_parameters_values_and_figure_binding(self):
        article = build(ARTICLE)
        self.assertEqual(
            article["parameters"],
            [{"name": "n", "labels": ["2 nodos", "4 nodos", "8 nodos"], "start": 1}],
        )
        self.assertEqual(
            article["values"],
            [
                {"parameter": 0, "text": ["2", "4", "8"], "input": True},
                {
                    "parameter": 0,
                    "text": ["2 nodos", "4 nodos", "8 nodos"],
                    "input": True,
                },
                {"parameter": 0, "text": ["4", "16", "64"], "input": False},
            ],
        )
        [prose], [figure] = (block["outputs"] for block in article["blocks"])
        # The same text twice is one value; each shows the start until the page runs.
        self.assertIn(
            r"Con $n = \qv{0}{4}$ hay \qv{1}{4 nodos}, \qv{2}{16} y \qv{2}{16}.",
            prose["text"],
        )
        self.assertEqual(figure["frames"]["parameter"], 0)

    def test_an_article_without_parameters_exports_only_blocks(self):
        article = build("```python\n1 + 1\n```\n")
        self.assertEqual(set(article), {"version", "blocks"})

    def test_a_value_that_would_break_its_placeholder_fails_the_build(self):
        source = '```python\nfrom quire import md, parameter\nk = parameter("k", ["a}", "b"])\nmd(f"{k}")\n```\n'
        with self.assertRaisesRegex(ArticleError, "cannot hold"):
            build(source)


class StandaloneParameterTest(unittest.TestCase):
    def test_outside_a_build_a_parameter_formats_as_its_start_value(self):
        n = parameter("n", [1.0, 2.5], value=2.5)
        self.assertEqual(f"{n:.1f} y {n.each(lambda v: v * 2):.0f}", "2.5 y 5")

    def test_a_start_value_must_be_one_of_the_values(self):
        with self.assertRaisesRegex(ValueError, "not one of the values"):
            parameter("n", [1, 2], value=3)
