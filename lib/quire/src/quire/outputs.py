"""Turn the value of a fence's last expression into a document output."""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class Markdown:
    text: str

    def __quire__(self) -> dict:
        return {"type": "markdown", "text": self.text}


def md(text: str) -> Markdown:
    """Markdown with math; an f-string puts computed values into prose."""
    return Markdown(dedent(text).strip("\n"))


def to_output(value: object) -> dict | None:
    if value is None:
        return None
    export = getattr(value, "__quire__", None)
    if callable(export):
        return export()
    text = value if isinstance(value, str) else repr(value)
    return {"type": "text", "text": text}
