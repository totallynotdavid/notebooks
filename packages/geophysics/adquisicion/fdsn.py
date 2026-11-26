"""Descarga trazas miniSEED y metadatos StationXML del sismo de Pisco de 2007.

Los servicios web FDSN reparten el archivo del centro de datos: `station`
responde los metadatos de estaciones en StationXML y `dataselect` responde
las formas de onda en miniSEED. `obspy.clients.fdsn` habla con ambos. Este
módulo renueva la copia de `data/fdsn/` que el artículo lee sin red.
"""

from __future__ import annotations

import datetime as dt
import itertools
from pathlib import Path

from obspy import Inventory, Stream, UTCDateTime, read, read_inventory
from obspy.clients.fdsn import Client
from obspy.geodetics import gps2dist_azimuth, locations2degrees
from obspy.taup import TauPyModel

# Hipocentro del sismo de Pisco, el que llevan las cabeceras de data/sac/.
EVENTO = {
    "origen": UTCDateTime("2007-08-15T23:40:58"),
    "evla": -13.3836,
    "evlo": -76.5555,
    "evdp": 41.2,
    "nombre": "Near Coast Of Peru",
}
# Las estaciones del conjunto de data/sac/, en el orden del catálogo.
REDES = "G,GE,II,IU"
CANAL = "BHZ"
ESTACIONES = (
    "KIP,MBO,MPG,TAM,TAOE",
    "SFJD",
    "ASCN,BORG,EFI,PFO,RPN,SUR",
    "ANMO,BBSR,COR,DWPF,KIP,PAB,PMSA,POHA,PTCN,QSPA,RSSD,SBA,SFJD,SJG,TSUM,TUC,WCI,XMAS",
)
ESTACIONES = tuple(",".join(ESTACIONES).split(","))
# Cada red vive en el datacentro que la opera; el resto va a EarthScope.
CENTROS = {"GE": "GEOFON"}
VENTANA = (-60.0, 720.0)

DATOS = Path(__file__).resolve().parent.parent / "data" / "fdsn"

NOTA = """\
# Datos FDSN del sismo de Pisco de 2007

Metadatos StationXML y trazas miniSEED de las estaciones del conjunto de
`data/sac/`, canal BHZ, descargados de los servicios web FDSN: EarthScope
(`https://service.iris.edu`) para los metadatos y las trazas de G, II e IU,
y el datacentro de GEOFON (`geofon.gfz.de`) para la traza de GE. La ventana
de cada traza es un minuto antes a doce minutos después de la llegada
teórica de la onda P en iasp91.

- Estaciones: {estaciones}
- Fecha de descarga: {fecha}
- Archivos: `estaciones.xml` (metadatos con respuesta instrumental) y un
  `*.mseed` por estación (formas de onda en miniSEED).

Para volver a descargar:
`uv run --package geophysics python -m adquisicion.fdsn`.
"""


def crear_cliente(centro: str = "EARTHSCOPE") -> Client:
    """Cliente FDSN de un datacentro; EarthScope es el antiguo IRIS DMC."""
    return Client(centro)


def clientes_por_red() -> dict:
    """Un cliente por datacentro, indexado por red."""
    return {
        red: crear_cliente(centro)
        for red, centro in {
            **{r: "EARTHSCOPE" for r in REDES.split(",")},
            **CENTROS,
        }.items()
    }


def distancia(canal) -> tuple[float, float, float, float]:
    """Distancia epicentral, azimut, retroazimut y distancia en km."""
    dist_m, az, baz = gps2dist_azimuth(
        EVENTO["evla"], EVENTO["evlo"], canal.latitude, canal.longitude
    )
    gcarc = locations2degrees(
        EVENTO["evla"], EVENTO["evlo"], canal.latitude, canal.longitude
    )
    return gcarc, az, baz, dist_m / 1000


def ventana_p(gcarc: float, modelo: TauPyModel) -> tuple[UTCDateTime, UTCDateTime]:
    """Intervalo alrededor de la llegada teórica de la onda P en iasp91."""
    p = modelo.get_travel_times(
        source_depth_in_km=EVENTO["evdp"],
        distance_in_degree=gcarc,
        phase_list=["P"],
    )[0].time
    inicio = EVENTO["origen"] + p + VENTANA[0]
    return inicio, inicio + VENTANA[1] - VENTANA[0]


def descargar_metadatos(cliente, estaciones=ESTACIONES) -> Inventory:
    """StationXML de las estaciones, con su respuesta instrumental."""
    return cliente.get_stations(
        network=REDES,
        station=",".join(estaciones),
        location="00",
        channel=CANAL,
        starttime=EVENTO["origen"],
        endtime=EVENTO["origen"] + 1,
        level="response",
    )


def descargar_trazas(cliente, inventario: Inventory, por_red=None) -> Stream:
    """Una traza miniSEED por canal del inventario, en su ventana de P."""
    modelo = TauPyModel("iasp91")
    trazas = Stream()
    for red in inventario:
        for estacion in red:
            for canal in estacion:
                inicio, fin = ventana_p(distancia(canal)[0], modelo)
                trazas += (
                    (por_red or {})
                    .get(red.code, cliente)
                    .get_waveforms(
                        red.code,
                        estacion.code,
                        canal.location_code,
                        canal.code,
                        inicio,
                        fin,
                    )
                )
    # miniSEED guarda los huecos como tramos separados; al unirlos quedan
    # enmascarados para no inventar muestras.
    trazas.merge()
    return trazas


def escribir_sac(tr, canal, destino: Path) -> Path:
    """Escribe la traza en SAC con cabecera de evento y estación."""
    gcarc, az, baz, dist = distancia(canal)
    tr.stats.sac = {
        "stla": canal.latitude,
        "stlo": canal.longitude,
        "stel": canal.elevation,
        "stdp": canal.depth,
        "cmpaz": canal.azimuth,
        "cmpinc": canal.dip,
        "evla": EVENTO["evla"],
        "evlo": EVENTO["evlo"],
        "evdp": EVENTO["evdp"],
        "kevnm": EVENTO["nombre"],
        "o": float(EVENTO["origen"] - tr.stats.starttime),
        "gcarc": gcarc,
        "az": az,
        "baz": baz,
        "dist": dist,
        "kinst": canal.sensor.description,
        "scale": canal.response.instrument_sensitivity.value,
    }
    ruta = destino / (f"{tr.id}.{tr.stats.starttime.strftime('%Y.%j.%H%M%S')}.SAC")
    tr.write(str(ruta), format="SAC")
    return ruta


class ClienteArchivo:
    """Cliente FDSN local: sirve la copia de `data/fdsn/` con la misma API.

    El artículo construye sin red, así que sus celdas llaman a este cliente
    en lugar de `Client("EARTHSCOPE")`; los argumentos son los mismos.
    """

    def __init__(self, carpeta: Path = DATOS):
        self._trazas = read(str(carpeta / "*.mseed"))
        self._inventario = read_inventory(str(carpeta / "estaciones.xml"))

    def get_stations(self, starttime=None, endtime=None, **seleccion):
        seleccion.pop("level", None)
        inventario = Inventory(networks=[], source=self._inventario.source)
        for sel in _expandir(seleccion):
            inventario += self._inventario.select(
                starttime=starttime, endtime=endtime, **sel
            )
        return inventario

    def get_waveforms(self, network, station, location, channel, starttime, endtime):
        trazas = Stream()
        for sel in _expandir(
            {
                "network": network,
                "station": station,
                "location": location,
                "channel": channel,
            }
        ):
            trazas += self._trazas.select(**sel)
        return trazas.slice(starttime, endtime)


def _expandir(seleccion: dict) -> list[dict]:
    """Convierte listas con comas en una combinación por elemento.

    Los servicios FDSN aceptan `network="IU,G"`; `select` no, así que cada
    combinación se consulta por separado.
    """
    claves = list(seleccion)
    partes = [str(seleccion[k]).split(",") for k in claves]
    return [
        dict(zip(claves, combo, strict=True)) for combo in itertools.product(*partes)
    ]


def write_snapshot(cliente, out_dir: Path, por_red=None) -> int:
    """Descarga la copia del artículo: XML de estaciones y un mseed por traza."""
    inventario = descargar_metadatos(cliente)
    trazas = descargar_trazas(cliente, inventario, por_red)
    out_dir.mkdir(parents=True, exist_ok=True)
    inventario.write(str(out_dir / "estaciones.xml"), format="STATIONXML")
    for tr in trazas:
        tr.write(str(out_dir / f"{tr.id}.mseed"), format="MSEED")
    (out_dir / "NOTA.md").write_text(
        NOTA.format(
            estaciones=", ".join(sorted({tr.stats.station for tr in trazas})),
            fecha=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"),
        ),
        encoding="utf-8",
    )
    return len(trazas)


if __name__ == "__main__":
    cliente = crear_cliente()
    por_red = {red: crear_cliente(centro) for red, centro in CENTROS.items()}
    print(f"{write_snapshot(cliente, DATOS, por_red)} trazas en {DATOS}")
