"""Compact JSON values for figure data."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

DIGITS = 5


def is_array(value: object) -> bool:
    return isinstance(value, np.ndarray | list | tuple | range)


def compact(values: object, digits: int = DIGITS) -> list:
    """Round floats to `digits` significant digits; NaN and inf become null.

    Plot draws a null as a gap in a line, so NaN keeps its meaning.
    """
    array = np.asarray(values)
    if array.dtype.kind in "iub":
        return array.tolist()
    if array.dtype.kind != "f":
        return [_scalar(v, digits) for v in _as_list(values)]
    return _round(array.astype(float), digits)


def _round(array: np.ndarray, digits: int) -> list:
    finite = np.isfinite(array)
    safe = np.where(finite & (array != 0), np.abs(array), 1.0)
    exponent = digits - 1 - np.floor(np.log10(safe))
    # Divide by an exact power of ten so each value prints as its short decimal.
    up = 10.0 ** np.clip(exponent, 0, None)
    down = 10.0 ** np.clip(-exponent, 0, None)
    rounded = np.where(
        exponent >= 0,
        np.round(array * up) / up,
        np.round(array / down) * down,
    )
    out = rounded.astype(object)
    out[~finite] = None
    return out.tolist()


def _scalar(value: object, digits: int) -> object:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return _round(np.array([value]), digits)[0]
    return value


def _as_list(values: object) -> Sequence:
    return values.tolist() if isinstance(values, np.ndarray) else list(values)


def plain(value: object, digits: int = DIGITS) -> object:
    """Convert an option value (nested dicts, lists, numpy scalars) to JSON."""
    if isinstance(value, dict):
        return {k: plain(v, digits) for k, v in value.items()}
    if is_array(value):
        return compact(value, digits)
    return _scalar(value, digits)
