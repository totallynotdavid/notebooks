"""Split an article into prose and Python fences."""

from __future__ import annotations

import re
from dataclasses import dataclass

FENCE_OPEN = re.compile(r"^(`{3,})python(?:\s+(?P<flags>[\w\s-]*))?\s*$")


@dataclass(frozen=True)
class Prose:
    text: str


@dataclass(frozen=True)
class Code:
    source: str
    line: int
    """1-based line of the first source line in the article."""
    hidden: bool


type Block = Prose | Code


def parse(text: str) -> list[Block]:
    blocks: list[Block] = []
    prose: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        opening = FENCE_OPEN.match(lines[i])
        if opening is None:
            prose.append(lines[i])
            i += 1
            continue

        fence = opening.group(1)
        flags = (opening.group("flags") or "").split()
        start = i + 1
        end = start
        while end < len(lines) and lines[end].rstrip() != fence:
            end += 1
        if end == len(lines):
            raise SyntaxError(f"line {i + 1}: python fence is never closed")

        _flush(prose, blocks)
        blocks.append(
            Code(
                source="\n".join(lines[start:end]),
                line=start + 1,
                hidden="hidden" in flags,
            )
        )
        i = end + 1
    _flush(prose, blocks)
    return blocks


def _flush(prose: list[str], blocks: list[Block]) -> None:
    text = "\n".join(prose).strip("\n")
    if text.strip():
        blocks.append(Prose(text))
    prose.clear()
