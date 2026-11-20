r"""Numbers the reader drags in an article's prose and math.

`parameter(name, values)` makes one. Formatting it in `md()` text, as in
`f"{amplitud}"`, writes a number the reader drags through `values`;
`amplitud.each(f)` formats as `f` of the current value and follows the drag.
A figure built with `frames=amplitud` draws the frame of the current value.

Formatting writes `\qv{k}{text}`: entry k of the document's `values`, which
shows `text` until the page script runs. Outside a build it writes the text.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field

import numpy as np

# Characters that would end the placeholder's group or its math.
_RESERVED = set("{}\\$")


@dataclass
class Registry:
    parameters: list[Parameter] = field(default_factory=list)
    values: dict[tuple, int] = field(default_factory=dict)

    def export(self) -> dict:
        if not self.parameters:
            return {}
        return {
            "parameters": [
                {"name": p.name, "labels": p.labels, "start": p.start}
                for p in self.parameters
            ],
            "values": [
                {"parameter": parameter, "text": list(text), "input": input}
                for parameter, text, input in self.values
            ],
        }


_registry: Registry | None = None


@contextlib.contextmanager
def collecting() -> Iterator[Registry]:
    """Record the parameters and values an article formats while it runs."""
    global _registry
    previous, _registry = _registry, Registry()
    try:
        yield _registry
    finally:
        _registry = previous


def _placeholder(parameter: Parameter, text: list[str], input: bool) -> str:
    for item in text:
        if _RESERVED & set(item):
            raise ValueError(f"{item!r}: a value cannot hold {{, }}, \\ or $")
    if _registry is None or parameter.index is None:
        return text[parameter.start]
    key = (parameter.index, tuple(text), input)
    index = _registry.values.setdefault(key, len(_registry.values))
    return rf"\qv{{{index}}}{{{text[parameter.start]}}}"


@dataclass(eq=False)
class Parameter:
    name: str
    values: np.ndarray
    start: int
    format: str
    index: int | None = None

    @property
    def labels(self) -> list[str]:
        return [self.format.format(value) for value in self.values]

    @property
    def value(self) -> object:
        return self.values[self.start]

    def __format__(self, spec: str) -> str:
        text = [format(value, spec) for value in self.values] if spec else self.labels
        return _placeholder(self, text, input=True)

    def each(self, values: Callable[[object], object] | Sequence) -> Derived:
        """A value per parameter value: `f(value)`, or the items of a list."""
        if callable(values):
            results = [values(value) for value in self.values]
        else:
            results = list(values)
            if len(results) != len(self.values):
                raise ValueError(
                    f"{len(results)} values for the {len(self.values)} of {self.name}"
                )
        return Derived(self, results)


@dataclass(eq=False)
class Derived:
    parameter: Parameter
    results: list

    @property
    def value(self) -> object:
        return self.results[self.parameter.start]

    def __format__(self, spec: str) -> str:
        text = [format(result, spec) for result in self.results]
        return _placeholder(self.parameter, text, input=False)


def parameter(
    name: str,
    values: Sequence,
    *,
    value: object = None,
    format: str = "{}",
) -> Parameter:
    """A number the reader drags through `values`, starting at `value`.

    `format` makes each value's label, as in `"{:.0f}°"`; a format spec in the
    f-string, as in `f"{p:.2f}"`, replaces it in that sentence.
    """
    array = np.asarray(values)
    if array.ndim != 1 or len(array) < 2:
        raise ValueError(f"{name}: values must be a list of two or more")
    if value is None:
        start = 0
    else:
        matches = np.flatnonzero(array == value)
        if matches.size == 0:
            raise ValueError(f"{name}: {value!r} is not one of the values")
        start = int(matches[0])
    made = Parameter(name, array, start, format)
    if _registry is not None:
        made.index = len(_registry.parameters)
        _registry.parameters.append(made)
    return made
