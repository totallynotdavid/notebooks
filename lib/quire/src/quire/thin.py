"""Drop the points of a figure that the screen cannot show.

Coordinates are first scaled to the unit square of the axis domains, so the
tolerance is a fraction of the figure's width in pixels.
"""

from __future__ import annotations

import numpy as np

# Half a pixel of a figure this wide is the error a reader cannot see.
WIDEST = 800
TOLERANCE = 0.5 / WIDEST


def unit(values: np.ndarray, axis: dict) -> np.ndarray:
    """`values` on the axis, scaled so its domain spans [0, 1]."""
    values = np.asarray(values, dtype=float)
    if axis.get("type") == "log":
        with np.errstate(divide="ignore", invalid="ignore"):
            values = np.where(values > 0, np.log10(values), np.nan)
    domain = axis.get("domain")
    if _is_pair(domain):
        low, high = sorted(float(d) for d in domain)
        if axis.get("type") == "log":
            low, high = np.log10(max(low, 1e-300)), np.log10(max(high, 1e-300))
    else:
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            return values
        low, high = finite.min(), finite.max()
    return (values - low) / (high - low if high > low else 1.0)


def _is_pair(domain: object) -> bool:
    return (
        isinstance(domain, list | tuple)
        and len(domain) == 2
        and all(isinstance(d, int | float) for d in domain)
    )


def line_points(x: np.ndarray, y: np.ndarray, tolerance: float) -> np.ndarray:
    """Indices of a polyline that stay within `tolerance` of it
    (Ramer-Douglas-Peucker). A non-finite point is a gap and is kept."""
    finite = np.isfinite(x) & np.isfinite(y)
    keep = ~finite
    starts = np.flatnonzero(finite & ~np.r_[False, finite[:-1]])
    ends = np.flatnonzero(finite & ~np.r_[finite[1:], False])
    for start, end in zip(starts, ends, strict=True):
        keep[start] = keep[end] = True
        stack = [(start, end)]
        while stack:
            first, last = stack.pop()
            if last - first < 2:
                continue
            inner = slice(first + 1, last)
            dx, dy = x[last] - x[first], y[last] - y[first]
            px, py = x[inner] - x[first], y[inner] - y[first]
            length = np.hypot(dx, dy)
            if length == 0:
                distance = np.hypot(px, py)
            else:
                distance = np.abs(dx * py - dy * px) / length
            farthest = int(np.argmax(distance))
            if distance[farthest] > tolerance:
                middle = first + 1 + farthest
                keep[middle] = True
                stack += [(first, middle), (middle, last)]
    return np.flatnonzero(keep)


def dot_points(x: np.ndarray, y: np.ndarray, tolerance: float) -> np.ndarray:
    """Indices of the first dot on each cell of a `tolerance` grid."""
    cells = np.stack([np.round(x / tolerance), np.round(y / tolerance)], axis=1)
    finite = np.isfinite(cells).all(axis=1)
    _, first = np.unique(cells[finite], axis=0, return_index=True)
    return np.sort(np.flatnonzero(finite)[first])
