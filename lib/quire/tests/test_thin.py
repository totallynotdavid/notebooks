"""Which points of a figure reach the page."""

from __future__ import annotations

import unittest

import numpy as np
from quire import plot as P
from quire.thin import TOLERANCE


def sent(figure: P.Figure) -> list[dict]:
    return [mark["channels"] for mark in figure.__quire__()["marks"]]


def distance_to_polyline(px, py, x, y) -> np.ndarray:
    """Distance from each point (px, py) to the nearest segment of (x, y)."""
    ax, ay, bx, by = x[:-1], y[:-1], x[1:], y[1:]
    dx, dy = bx - ax, by - ay
    t = ((px[:, None] - ax) * dx + (py[:, None] - ay) * dy) / (dx**2 + dy**2)
    t = np.clip(t, 0, 1)
    return np.hypot(ax + t * dx - px[:, None], ay + t * dy - py[:, None]).min(axis=1)


class LineTest(unittest.TestCase):
    def test_a_dense_curve_keeps_every_point_within_half_a_pixel(self):
        t = np.linspace(0, 1, 20_000)
        y = np.sin(12 * t) + 0.3 * np.sin(97 * t)
        [channels] = sent(P.figure(P.line(x=t, y=y)))
        x_sent, y_sent = np.array(channels["x"]), np.array(channels["y"])
        self.assertLess(x_sent.size, 2_000)
        scale = np.ptp(y)
        error = distance_to_polyline(
            t, (y - y.min()) / scale, x_sent, (y_sent - y.min()) / scale
        )
        # Rounding to 5 digits adds up to 5e-5 of the range.
        self.assertLess(error.max(), TOLERANCE + 1e-4)

    def test_a_gap_stays_a_gap(self):
        y = np.linspace(0, 1, 1_000)
        y[500] = np.nan
        [channels] = sent(P.figure(P.line(x=np.arange(1_000), y=y)))
        self.assertEqual(channels["x"], [0, 499, 500, 501, 999])
        self.assertIsNone(channels["y"][2])

    def test_a_line_over_names_is_sent_whole(self):
        names = [f"band {k}" for k in range(1_000)]
        [channels] = sent(P.figure(P.line(x=names, y=np.zeros(1_000))))
        self.assertEqual(len(channels["x"]), 1_000)

    def test_a_straight_line_on_a_log_axis_keeps_its_ends(self):
        t = np.linspace(0, 5, 1_000)
        log = sent(P.figure(P.line(x=t, y=10**t), y={"type": "log"}))
        linear = sent(P.figure(P.line(x=t, y=10**t)))
        self.assertEqual(len(log[0]["x"]), 2)
        self.assertGreater(len(linear[0]["x"]), 20)

    def test_each_z_group_is_its_own_line(self):
        t = np.repeat(np.linspace(0, 1, 500), 2)
        z = np.tile(["a", "b"], 500)
        y = np.where(z == "a", t, 1 - t)
        [channels] = sent(P.figure(P.line(x=t, y=y, z=z)))
        self.assertEqual(channels["z"], ["a", "b", "a", "b"])
        self.assertEqual(channels["y"], [0.0, 1.0, 1.0, 0.0])


class DotTest(unittest.TestCase):
    def test_dots_on_one_pixel_send_one(self):
        x = np.r_[np.zeros(100), 1.0]
        [channels] = sent(P.figure(P.dot(x=x, y=x)))
        self.assertEqual(channels["x"], [0.0, 1.0])

    def test_dots_with_their_own_color_are_all_sent(self):
        x = np.r_[np.zeros(100), 1.0]
        [channels] = sent(P.figure(P.dot(x=x, y=x, fill=np.arange(101))))
        self.assertEqual(len(channels["x"]), 101)


if __name__ == "__main__":
    unittest.main()
