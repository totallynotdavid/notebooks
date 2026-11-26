```python hidden
import tempfile
import warnings
from pathlib import Path

import numpy as np
from obspy import UTCDateTime, read
from obspy.taup import TauPyModel
from quire import md
from quire import plot as P
from quire import table as tabla

from adquisicion import fdsn

DATOS = Path(__file__).resolve().parent / "data"
ORIGEN = fdsn.EVENTO["origen"]

# La página construye sin red: `cliente` sirve la copia de data/fdsn/ con la
# misma interfaz que Client("EARTHSCOPE").
cliente = fdsn.ClienteArchivo(DATOS / "fdsn")

# ObsPy avisa que el delta del SAC se redondea a microsegundos.
warnings.filterwarnings("ignore", message="Sample spacing read from SAC file")
```

# Adquisición de registros sísmicos

El análisis de ondas de cuerpo telesísmicas empieza por conseguir dos cosas por
estación: la forma de onda registrada y los metadatos que la interpretan. Este
artículo consigue ambas para el terremoto de Pisco del 15 de agosto de 2007 (Mw
8.0) y escribe los registros en formato SAC, dejando los datos donde empieza
[Registros SAC con ObsPy](../sac-processing/), el artículo que los procesa.

Antes esto se hacía con otra cadena de herramientas: un script pedía miniSEED y
XML a las APIs HTTP de IRIS, el programa Java `stationxml-seed-converter`
escribía un dataless SEED y `rdseed` lo convertía a SAC. Ese camino murió:
`rdseed` perdió soporte en 2018 y su licencia no permite redistribuirlo, SAC se
distribuye solo a pedido y la descarga de SAC del portal Wilber 3 se descontinuó
en 2021. El camino actual es más corto: los servicios web FDSN y ObsPy hacen
todo en Python.

## Los servicios web FDSN

La FDSN (Federación de Redes Sismográficas Digitales) define servicios web que
los centros de datos sísmicos implementan. Dos bastan para la adquisición:

- `station` responde los metadatos de estaciones en formato StationXML:
  coordenadas, equipamiento y la respuesta instrumental completa.
- `dataselect` responde las formas de onda en formato miniSEED.

`obspy.clients.fdsn.Client` habla con ambos. `Client("EARTHSCOPE")` apunta al
centro de datos de EarthScope, el antiguo IRIS DMC.

Esta página corre sin red: lee una copia guardada en `data/fdsn/` a través de un
cliente local con la misma interfaz, así que las llamadas de abajo son las
mismas que haría `Client("EARTHSCOPE")` en vivo. Para volver a descargar la
copia:

```sh
uv run --package geophysics python -m adquisicion.fdsn
```

## El sismo y las estaciones

```python hidden
md(
    f"""
    El hipocentro es el que llevan las cabeceras SAC de `data/sac/`: origen
    {ORIGEN.strftime("%Y-%m-%d %H:%M:%S")} UTC, latitud
    {fdsn.EVENTO["evla"]}°, longitud {fdsn.EVENTO["evlo"]}°, profundidad
    {fdsn.EVENTO["evdp"]:g} km. Las estaciones del conjunto son de las redes
    G (GEOSCOPE), II e IU (Global Seismograph Network) y GE (GEOFON), entre
    30° y 90° de distancia epicentral: la ventana telesísmica, donde la onda
    P cruza el manto sin tocar el núcleo. El canal es BHZ, la componente
    vertical de banda ancha que muestrea a unas 20 muestras por segundo.
    """
)
```

```python
inventario = cliente.get_stations(
    network=fdsn.REDES,
    station=",".join(fdsn.ESTACIONES),
    location="00",
    channel="BHZ",
    starttime=ORIGEN,
    endtime=ORIGEN + 1,
    level="response",
)
```

`get_stations` pide el StationXML de los treinta canales del conjunto: las redes
`"G,GE,II,IU"` y las estaciones de `fdsn.ESTACIONES`, las mismas que guarda
`data/sac/`. La red y la estación aceptan listas con comas; `location` es el
código de ubicación del canal (las estaciones pueden tener varios sensores en
sitios distintos del recinto) y `channel` el código de canal SEED. La ventana de
tiempo limita la consulta a las épocas en que el canal registraba.
`level="response"` baja la respuesta instrumental completa —la sensibilidad y
los polos y ceros que describen el sensor—; con `level="channel"` bastaría para
las coordenadas.

```python hidden
tabla(
    ["estación", "latitud (°)", "longitud (°)", "elevación (m)", "sensor"],
    [
        [
            f"{red.code}.{est.code}",
            f"{ch.latitude}",
            f"{ch.longitude}",
            f"{ch.elevation:g}",
            ch.sensor.description,
        ]
        for red in inventario
        for est in red
        for ch in est.channels
    ],
)
```

## Las formas de onda

La ventana de cada descarga se arma alrededor de la llegada teórica de la onda P
en el modelo iasp91, desde un minuto antes hasta doce minutos después: basta
para la P y su coda, que es lo que el análisis de ondas de cuerpo usa.

```python
modelo = TauPyModel("iasp91")


def ventana_p(gcarc):
    p = modelo.get_travel_times(
        source_depth_in_km=fdsn.EVENTO["evdp"],
        distance_in_degree=gcarc,
        phase_list=["P"],
    )[0].time
    return ORIGEN + p - 60, ORIGEN + p + 720
```

```python
inicio, fin = ventana_p(56.0)
tr = cliente.get_waveforms("IU", "TUC", "00", "BHZ", inicio, fin)[0]
tr
```

`get_waveforms` pide un canal por red, estación, ubicación y código SEED, en el
intervalo `[inicio, fin]`, y devuelve un `Stream` de trazas. La descarga de las
treinta estaciones repite la llamada por canal del inventario:

```python
trazas = fdsn.descargar_trazas(cliente, inventario)
```

Una red no siempre vive en el mismo datacentro que la consulta: EarthScope tiene
los metadatos de GE.SFJD pero no sus trazas de 2007, que las sirve el datacentro
de GEOFON. `descargar_trazas` acepta un cliente por red (`por_red`) para
pedirlas allí; la copia de `data/fdsn/` ya las trajo así.

La sección de abajo ordena las trazas por distancia, normaliza cada una por su
máximo y mide el tiempo desde el origen del sismo. La forma de onda llega en
cuentas del digitalizador, sin quitar la respuesta del instrumento.

```python hidden
seccion = []
for tr in trazas:
    ch = inventario.select(network=tr.stats.network, station=tr.stats.station)[0][0][0]
    gcarc, az, baz, _dist = fdsn.distancia(ch)
    seccion.append((gcarc, tr))
seccion.sort(key=lambda par: par[0])
ts, ys, gs = [], [], []
for i, (gcarc, tr) in enumerate(seccion):
    t = tr.times() + float(tr.stats.starttime - ORIGEN)
    ts.append(t)
    ys.append(i + 0.45 * tr.data / abs(tr.data).max())
    gs.append(np.full(t.size, i))
P.figure(
    P.line(
        x=np.concatenate(ts),
        y=np.concatenate(ys),
        z=np.concatenate(gs),
        stroke="currentColor",
        strokeWidth=0.6,
        tip=False,
    ),
    P.text(
        x=[0] * len(seccion),
        y=list(range(len(seccion))),
        text=[f"{tr.id} {gcarc:.1f}°" for gcarc, tr in seccion],
        textAnchor="start",
        dx=6,
        fontSize=11,
    ),
    title="Pisco 2007, BHZ, ordenado por distancia",
    x={"label": "tiempo desde el origen (s)", "domain": [250, 1600]},
    y={"axis": None, "domain": [-1, len(seccion)]},
    grid=True,
    height=600,
    digits=4,
)
```

## De miniSEED a SAC

SAC es el formato del software Seismic Analysis Code: una cabecera binaria fija
seguida de la serie temporal. El miniSEED ya trae la serie y su tasa de
muestreo; lo que falta lo aportan el StationXML (posición del sensor y
sensibilidad) y el evento (hipocentro y tiempo origen). `tr.write` con
`format="SAC"` escribe el archivo una vez lleno `tr.stats.sac`.

```python
def escribir_sac(tr, canal, destino):
    gcarc, az, baz, dist = fdsn.distancia(canal)
    tr.stats.sac = {
        # La estación, del StationXML.
        "stla": canal.latitude,
        "stlo": canal.longitude,
        "stel": canal.elevation,
        "stdp": canal.depth,
        "cmpaz": canal.azimuth,
        "cmpinc": canal.dip,
        "kinst": canal.sensor.description,
        "scale": canal.response.instrument_sensitivity.value,
        # El evento.
        "evla": fdsn.EVENTO["evla"],
        "evlo": fdsn.EVENTO["evlo"],
        "evdp": fdsn.EVENTO["evdp"],
        "kevnm": fdsn.EVENTO["nombre"],
        "o": float(ORIGEN - tr.stats.starttime),
        # Distancia y acimutes, calculados.
        "gcarc": gcarc,
        "az": az,
        "baz": baz,
        "dist": dist,
    }
    ruta = destino / f"{tr.id}.{tr.stats.starttime.strftime('%Y.%j.%H%M%S')}.SAC"
    tr.write(str(ruta), format="SAC")
    return ruta


salida = Path(tempfile.mkdtemp())
escritos = [
    escribir_sac(
        tr,
        inventario.select(network=tr.stats.network, station=tr.stats.station)[0][0][0],
        salida,
    )
    for tr in trazas
]
```

Tres campos merecen una nota:

- `o` es el tiempo origen del evento, en segundos desde la hora de referencia
  del archivo. Con él el tiempo de la serie se reexpresa desde el origen del
  sismo, como en la figura de arriba.
- `scale` es la sensibilidad del instrumento, en cuentas por unidad física. La
  serie sigue en cuentas: quitar la respuesta exige los polos y ceros del
  StationXML, que el archivo SAC no guarda.
- `kinst` nombra el instrumento; la cabecera lo corta a ocho caracteres.

```python hidden
leidos = [read(p)[0] for p in escritos]
tabla(
    ["archivo", "distancia (°)", "o (s)", "evdp (km)", "scale", "kinst"],
    [
        [
            p.name,
            f"{tr.stats.sac['gcarc']:.2f}",
            f"{tr.stats.sac['o']:.1f}",
            f"{tr.stats.sac['evdp']:.1f}",
            f"{tr.stats.sac['scale']:.3g}",
            tr.stats.sac["kinst"],
        ]
        for p, tr in zip(escritos, leidos, strict=True)
    ],
)
```

## Comprobación contra el conjunto guardado

Los archivos BHZ de `data/sac/` son los que el siguiente artículo procesa. Para
IU.TUC el registro recién escrito y el guardado comparten muestras y cabecera.

```python hidden
referencia = read(DATOS / "sac" / "IU.TUC.00.BHZ.M.2007.227.234933.SAC")[0]
nuevo = [tr for tr in leidos if tr.stats.station == "TUC"][0]
desfase = round(
    float(nuevo.stats.starttime - referencia.stats.starttime)
    * referencia.stats.sampling_rate
)
n = nuevo.stats.npts
muestras_iguales = bool(
    np.array_equal(
        referencia.data[desfase : desfase + n].astype(np.int64),
        nuevo.data.astype(np.int64),
    )
)
md(
    f"""
    La ventana descargada aquí empieza {desfase} muestras después de la del
    archivo guardado, pero las {n} muestras del tramo común
    {"coinciden una a una" if muestras_iguales else "difieren"}
    y ambas cabeceras fijan el mismo instante de origen
    ({ORIGEN.strftime("%H:%M:%S")} UTC). La distancia sale
    {nuevo.stats.sac["gcarc"]:.2f}° frente a
    {referencia.stats.sac["gcarc"]:.2f}° del guardado: el archivo viejo la
    calculó con otra geodesia, una diferencia que no cambia la onda.
    """
)
```

De aquí en adelante el conjunto se procesa en
[Registros SAC con ObsPy](../sac-processing/): quita la tendencia, filtra, pica
la onda P con STA/LTA y calcula espectros.
