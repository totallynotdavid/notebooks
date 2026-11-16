"""Figure specs that the site draws with Observable Plot.

A mark mirrors a Plot mark: `line(x=t, y=e)` becomes `Plot.line` with those
arrays as channels. An array option is a channel; any other option passes to
Plot unchanged. `series="RK4"` names the mark in the color legend.

A figure with `frames` animates. A channel with one row per frame, shape
(frames, n), changes with the frame; every other channel is drawn once.
A `since` channel holds the frame that first draws each element, so points
that accumulate are sent once. Animated figures in one `grid` share a player.
With `parameter`, the frames are values the reader picks with a slider.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from quire.encode import DIGITS, compact, is_array, plain


@dataclass
class Mark:
    kind: str
    data: object = None
    options: dict = field(default_factory=dict)

    def encode(self, frames: int | None, digits: int) -> dict:
        channels: dict[str, object] = {}
        animated: dict[str, object] = {}
        options: dict[str, object] = {}
        for name, value in self.options.items():
            if name == "series":
                continue
            if not is_array(value):
                options[name] = plain(value, digits)
                continue
            array = np.asarray(value)
            if frames is not None and array.ndim == 2 and len(array) == frames:
                animated[name] = compact(array, digits)
            else:
                channels[name] = compact(array, digits)
        spec: dict[str, object] = {"kind": self.kind, "options": options}
        if self.data is not None:
            spec["data"] = compact(self.data, digits)
        if channels:
            spec["channels"] = channels
        if animated:
            spec["animated"] = animated
        if "series" in self.options:
            spec["series"] = str(self.options["series"])
        return spec


def _mark(kind: str):
    def make(data: object = None, /, **options: object) -> Mark:
        return Mark(kind, data, options)

    make.__name__ = kind
    make.__doc__ = f"Plot.{kind}"
    return make


area = _mark("area")
areaX = _mark("areaX")
areaY = _mark("areaY")
arrow = _mark("arrow")
barX = _mark("barX")
barY = _mark("barY")
cell = _mark("cell")
dot = _mark("dot")
geo = _mark("geo")
line = _mark("line")
link = _mark("link")
raster = _mark("raster")
rect = _mark("rect")
rectX = _mark("rectX")
rectY = _mark("rectY")
ruleX = _mark("ruleX")
ruleY = _mark("ruleY")
text = _mark("text")
tickX = _mark("tickX")
tickY = _mark("tickY")


@dataclass
class Figure:
    marks: list[Mark]
    options: dict
    frames: list[str] | None = None
    fps: float = 20
    digits: int = DIGITS
    parameter: str | None = None
    start: int = 0

    def __quire__(self) -> dict:
        count = None if self.frames is None else len(self.frames)
        spec: dict[str, object] = {
            "type": "plot",
            "marks": [mark.encode(count, self.digits) for mark in self.marks],
            "options": plain(self.options, self.digits),
        }
        if self.frames is not None:
            frames: dict[str, object] = {"labels": list(self.frames), "fps": self.fps}
            if self.parameter is not None:
                frames |= {"parameter": self.parameter, "start": self.start}
            spec["frames"] = frames
        return spec


def figure(
    *marks: Mark,
    frames: list[str] | None = None,
    fps: float = 20,
    digits: int = DIGITS,
    parameter: str | None = None,
    start: int = 0,
    **options: object,
) -> Figure:
    """A Plot figure. `frames` labels each frame; options go to Plot.plot.

    With `parameter`, each frame is one value of that parameter: the reader
    picks it with a slider that starts at frame `start`, and nothing plays.
    """
    if parameter is not None:
        if frames is None:
            raise ValueError("parameter needs frames, one per value")
        if not 0 <= start < len(frames):
            raise ValueError(f"start {start} is outside the {len(frames)} frames")
    return Figure(list(marks), options, frames, fps, digits, parameter, start)


@dataclass
class Grid:
    figures: list[Figure]

    def __quire__(self) -> dict:
        return {"type": "grid", "figures": [f.__quire__() for f in self.figures]}


def grid(*figures: Figure) -> Grid:
    """Figures side by side; they wrap to one column on a narrow page."""
    return Grid(list(figures))
