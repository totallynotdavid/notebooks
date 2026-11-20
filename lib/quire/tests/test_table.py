"""Which columns of a table the site sets as numbers."""

from __future__ import annotations

import unittest

import numpy as np
from quire import table


class TableAlignment(unittest.TestCase):
    def test_only_columns_of_numbers_align_right(self):
        text = table(
            ["banda", "intervalo (µm)", "ganancia", "error", "conjunto", "estado"],
            [
                [
                    "azul",
                    "0.450–0.520",
                    np.float64(0.2),
                    "+1.2e-3",
                    "`USGS/SRTM`",
                    "ok",
                ],
                ["rojo", "0.630–0.690", 7, "", "`ECMWF/ERA5`", "revisar"],
            ],
        ).text
        self.assertEqual(
            text.splitlines()[1], "| --- | ---: | ---: | ---: | --- | --- |"
        )

    def test_the_first_column_labels_rows(self):
        text = table(["n", "error"], [[1, "3%"], [2, "4%"]]).text
        self.assertEqual(text.splitlines()[1], "| --- | ---: |")


if __name__ == "__main__":
    unittest.main()
