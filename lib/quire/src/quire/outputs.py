"""Turn the value of a fence's last expression into a document output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from numbers import Number
from textwrap import dedent


@dataclass(frozen=True)
class Markdown:
    text: str

    def __quire__(self) -> dict:
        return {"type": "markdown", "text": self.text}


def md(text: str) -> Markdown:
    """Markdown with math; an f-string puts computed values into prose."""
    return Markdown(dedent(text).strip("\n"))


# A number, a percentage, or a range of numbers such as 0.450–0.520.
NUMBER = re.compile(r"[+\-−]?[\d.,]+(e[+\-−]?\d+)?%?(–[+\-−]?[\d.,]+(e[+\-−]?\d+)?%?)?")


def is_number(cell: object) -> bool:
    if isinstance(cell, bool):
        return False
    if isinstance(cell, Number):
        return True
    text = str(cell).strip()
    return text == "" or NUMBER.fullmatch(text) is not None


def table(header: list[str], rows: list[list[object]]) -> Markdown:
    """A Markdown table. The site sets a column of numbers in mono, aligned
    right and on one line, and wraps any other column."""
    columns = list(zip(*rows, strict=True)) if rows else [()] * len(header)
    align = [
        "---:" if i > 0 and all(map(is_number, cells)) else "---"
        for i, cells in enumerate(columns)
    ]
    lines = [header, align, *([str(cell) for cell in row] for row in rows)]
    return Markdown("\n".join("| " + " | ".join(line) + " |" for line in lines))


def to_output(value: object) -> dict | None:
    if value is None:
        return None
    export = getattr(value, "__quire__", None)
    if callable(export):
        return export()
    text = value if isinstance(value, str) else repr(value)
    return {"type": "text", "text": text}
