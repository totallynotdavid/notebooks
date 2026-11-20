```python hidden
import json
from pathlib import Path

import numpy as np
from quire import md
from quire import plot as P
from quire import table as tabla

DATOS = json.loads(
    (Path(__file__).resolve().parent / "data" / "peru_earth_engine.json").read_text()
)
```

# Earth Engine en el Perú

Este artículo compara Lima, Cusco e Iquitos con tres productos de Google Earth
Engine: la elevación SRTM, la cobertura del suelo MODIS MCD12Q1 y la temperatura
superficial MODIS MOD11A1.

Las consultas a Earth Engine necesitan una cuenta y red, así que el artículo lee
sus resultados de `data/peru_earth_engine.json`. Para repetirlas, configura
`EE_PROJECT` en el `.env` del paquete y ejecuta `prepare_earth_engine.py`, que
reescribe ese archivo.

```python hidden
md(
    f"""
    El archivo se generó el {DATOS["generated_on"]}. Todas las coordenadas
    están en grados, como longitud y latitud.
    """
)
```

## Los tres lugares

```python hidden
tabla(
    ["lugar", "región", "longitud", "latitud"],
    [
        [p["name"], p["description"], f"{p['longitude']:.4f}", f"{p['latitude']:.4f}"]
        for p in DATOS["places"]
    ],
)
```

## Elevación SRTM

```python hidden
elevacion = DATOS["datasets"]["elevation"]
md(
    f"""
    La misión SRTM midió la elevación en febrero de 2000. El conjunto
    `{elevacion["id"]}` tiene una resolución de un segundo de arco, unos 30 m.
    """
)
```

```python hidden
tabla(
    ["lugar", "elevación (m)"],
    [[e["place"], e["elevation_m"]] for e in DATOS["elevation"]],
)
```

## Cobertura del suelo MODIS

```python hidden
cobertura = DATOS["datasets"]["land_cover"]
md(
    f"""
    La clase viene de la banda `LC_Type1` (clasificación IGBP) de
    `{cobertura["id"]}`, con fecha {cobertura["date"]}, en el píxel de 500 m
    que contiene cada punto.
    """
)
```

```python hidden
tabla(
    ["lugar", "código", "clase"],
    [[c["place"], c["class_code"], c["class_name"]] for c in DATOS["land_cover"]],
)
```

## Temperatura superficial mensual

MOD11A1 da la temperatura superficial diurna cada día con píxeles de 1 km. Se
conservan solo los píxeles cuyo `QC_Day` tiene los bits 0-1 en 00 (calidad
buena) y el bit 2 en 0. Los valores se multiplican por la escala de 0.02 K y se
pasan a °C. Cada punto es la media, en un radio de 5 km, del compuesto de
mediana del mes.

```python
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
lugares = [p["name"] for p in DATOS["places"]]
lst = {
    lugar: np.array(
        [
            np.nan if r["lst_celsius"] is None else r["lst_celsius"]
            for r in DATOS["land_surface_temperature"]
            if r["place"] == lugar
        ]
    )
    for lugar in lugares
}
```

```python hidden
mes = np.arange(1, 13)
P.figure(
    *(P.line(x=mes, y=lst[lugar], series=lugar, marker="circle") for lugar in lugares),
    title="MODIS MOD11A1: temperatura superficial diurna en 2025",
    x={"label": "mes de 2025 (1 = enero)", "ticks": mes.tolist()},
    y={"label": "temperatura (°C)"},
    grid=True,
)
```

```python hidden
sin_datos = [MESES[i] for i in np.flatnonzero(np.isnan(lst["Lima"]))]
md(
    f"""
    Lima no tiene píxeles válidos en {", ".join(sin_datos[:-1])} y {sin_datos[-1]}: la niebla costera
    del invierno cubre la ciudad y el filtro de calidad descarta esos días.
    Cusco, a más de 3000 m, es el más frío de los tres todo el año. Iquitos, en
    la Amazonía, varía poco entre meses.
    """
)
```
