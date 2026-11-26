"""Run the FDSN acquisition article and check the records it writes."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from obspy import read
from quire import article_namespace

PACKAGE = Path(__file__).resolve().parents[1]


class AdquisicionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defs = article_namespace(PACKAGE / "adquisicion_fdsn.md", use_cache=False)

    def test_escribe_un_sac_por_estacion(self):
        escritos = self.defs["escritos"]
        esperado = {
            nombre.name.removesuffix(".SAC").rsplit(".", 4)[0]
            for nombre in (PACKAGE / "data" / "sac").iterdir()
            if "filtered" not in nombre.name
        }
        for p in escritos:
            self.assertTrue(p.exists(), p)
        self.assertEqual(esperado, {Path(p).stem.rsplit(".", 3)[0] for p in escritos})

    def test_cabeceras_sac_tienen_evento_y_distancia(self):
        for tr in self.defs["leidos"]:
            sac = tr.stats.sac
            self.assertEqual(tr.stats.channel, "BHZ")
            self.assertEqual(sac["evdp"], 41.2)
            self.assertTrue(30.0 <= sac["gcarc"] <= 90.0, tr.id)
            # o negativo: la traza empieza después del origen del sismo.
            self.assertLess(sac["o"], 0)
            self.assertGreater(sac["scale"], 0)

    def test_tuc_reproduce_el_registro_guardado(self):
        leidos = {tr.stats.station: tr for tr in self.defs["leidos"]}
        referencia = read(
            PACKAGE / "data" / "sac" / "IU.TUC.00.BHZ.M.2007.227.234933.SAC"
        )[0]
        nuevo = leidos["TUC"]
        desfase = round(
            float(nuevo.stats.starttime - referencia.stats.starttime)
            * referencia.stats.sampling_rate
        )
        n = nuevo.stats.npts
        np.testing.assert_array_equal(
            referencia.data[desfase : desfase + n], nuevo.data
        )
        # El origen absoluto (inicio + o) es el mismo instante en ambos.
        origen_ref = referencia.stats.starttime + referencia.stats.sac["o"]
        origen_nuevo = nuevo.stats.starttime + nuevo.stats.sac["o"]
        self.assertAlmostEqual(float(origen_ref), float(origen_nuevo), places=2)
