```python hidden
from pathlib import Path

import numpy as np
import rasterio
from quire import md
from rasterio.transform import array_bounds
from rasterio.warp import transform_bounds
from quire import plot as P

ESCENA = (
    Path(__file__).resolve().parent
    / "data"
    / "landsat_scene_007068_20240427_reflectance.tif"
)
```

# Lectura de un raster Landsat con rasterio

Rasterio abre un raster como un _dataset_ con una o más bandas. Este artículo
abre un recorte de una escena Landsat 8, consulta su metadata, lee las bandas
como arreglos de NumPy y calcula con ellas un índice de vegetación.

El recorte está en `data/`. Lo genera `prepare_landsat.py` desde Google Earth
Engine con `EE_PROJECT` en el `.env` del paquete.

## Metadata

```python
with rasterio.open(ESCENA) as dataset:
    bandas = dataset.read()
    nodata = dataset.nodata
    metadata = {
        "count": dataset.count,
        "width": dataset.width,
        "height": dataset.height,
        "dtype": dataset.dtypes[0],
        "crs": dataset.crs,
        "transform": dataset.transform,
        "res": dataset.res,
        "descriptions": dataset.descriptions,
        "tags": dataset.tags(),
    }
```

```python hidden
t = metadata["transform"]
epsg = metadata["crs"].to_epsg()
hemisferio = {326: "norte", 327: "sur"}[epsg // 100]
y_negativa = (
    ". El recorte está al sur del ecuador, así que en esta zona su coordenada"
    " $y$ es negativa"
    if hemisferio == "norte" and t.f < 0
    else ""
)
md(
    f"""
    - Producto: `{metadata["tags"]["LANDSAT_PRODUCT_ID"]}`, de la colección
      `{metadata["tags"]["EARTH_ENGINE_COLLECTION"]}`.
    - Dimensiones: {metadata["width"]} columnas por {metadata["height"]} filas.
    - Bandas: {metadata["count"]}, llamadas `{", ".join(metadata["descriptions"])}`.
    - Tipo de dato: `{metadata["dtype"]}`. Valor NoData: `{nodata}`.
    - CRS: `{metadata["crs"]}`, UTM zona {epsg % 100} {hemisferio}{y_negativa}.
    - Píxel de {metadata["res"][0]:.0f} m. La esquina superior izquierda está en
      ({t.c:.0f}, {t.f:.0f}) m.
    """
)
```

La transformación afín lleva una fila y una columna a coordenadas del CRS. Con
ella se ubica cualquier píxel:

```python
fila, columna = 186, 219
x, y = metadata["transform"] * (columna + 0.5, fila + 0.5)
```

```python hidden
md(f"El centro del píxel ({fila}, {columna}) está en x = {x:.0f} m, y = {y:.0f} m.")
```

## NoData

Rasterio entrega el valor NoData pero no lo aplica: `read()` devuelve el arreglo
completo. Un arreglo enmascarado de NumPy deja fuera esos píxeles de cualquier
cálculo.

```python
enmascaradas = np.ma.masked_equal(bandas, nodata)
```

```python hidden
md(
    f"""
    En este recorte hay {int(enmascaradas.mask.sum())} píxeles con NoData, así
    que la máscara no excluye nada. En el borde de una escena completa, en
    cambio, el valor 0 marca los píxeles fuera de la franja del satélite.
    """
)
```

## Los valores de las bandas

La colección es de nivel 1: cada valor es un número digital (DN) cuantizado a 16
bits, no una reflectancia. La mediana de cada banda en el recorte es:

```python hidden
NOMBRES = {
    "B1": "aerosol costero (0.44 µm)",
    "B2": "azul (0.48 µm)",
    "B3": "verde (0.56 µm)",
    "B4": "rojo (0.65 µm)",
    "B5": "NIR (0.86 µm)",
    "B6": "SWIR 1 (1.61 µm)",
    "B7": "SWIR 2 (2.20 µm)",
}
mediana = np.ma.median(enmascaradas.reshape(len(bandas), -1), axis=1)
P.figure(
    P.barY(
        x=[NOMBRES[b] for b in metadata["descriptions"]],
        y=np.asarray(mediana, dtype=float),
        fill="currentColor",
        fillOpacity=0.6,
    ),
    title="Mediana de cada banda",
    x={"label": None, "domain": list(NOMBRES.values()), "tickRotate": -20},
    y={"label": "DN", "grid": True},
    marginBottom=70,
)
```

## Índice de vegetación

El NDVI compara el rojo, que la clorofila absorbe, con el infrarrojo cercano,
que la hoja refleja:

$$\mathrm{NDVI} = \frac{\mathrm{NIR} - \mathrm{rojo}}{\mathrm{NIR} + \mathrm{rojo}}$$

Con DN el índice no es el NDVI de reflectancia: cada banda tiene su propia
ganancia y su propio desplazamiento, así que el valor de un píxel cambia y los
umbrales publicados para reflectancia no se aplican tal cual.

```python
rojo = enmascaradas[3].astype(float)
nir = enmascaradas[4].astype(float)
ndvi = (nir - rojo) / (nir + rojo)
```

```python hidden
paso = 2
vista = ndvi[::paso, ::paso].filled(np.nan)
alto, ancho = vista.shape
P.figure(
    P.raster(
        fill=vista.ravel(),
        width=ancho,
        height=alto,
        x1=0,
        y1=0,
        x2=metadata["width"],
        y2=metadata["height"],
        imageRendering="pixelated",
    ),
    title="NDVI del recorte (un píxel de cada dos)",
    color={"scheme": "BrBG", "domain": [-0.5, 0.5], "legend": True, "label": "NDVI"},
    x={"label": "columna", "domain": [0, metadata["width"]]},
    y={"label": "fila", "domain": [metadata["height"], 0]},
    aspectRatio=1,
    width=560,
    digits=2,
)
```

```python hidden
limites = array_bounds(metadata["height"], metadata["width"], metadata["transform"])
oeste, sur, este, norte = transform_bounds(metadata["crs"], "EPSG:4326", *limites)
fecha = metadata["tags"]["LANDSAT_PRODUCT_ID"].split("_")[3]
negativos = float((ndvi < 0).mean())
md(
    f"""
    El recorte cubre {(limites[2] - limites[0]) / 1000:.1f} km por
    {(limites[3] - limites[1]) / 1000:.1f} km de los Andes del centro del
    Perú, con centro en {-(sur + norte) / 2:.2f}° S y
    {-(oeste + este) / 2:.2f}° O, y la escena se tomó el
    {fecha[6:]}/{fecha[4:6]}/{fecha[:4]}. La mediana del índice es
    {float(np.ma.median(ndvi)):.2f}, y el {float((ndvi > 0.3).mean()):.0%} de
    los píxeles pasa de 0.3. El {negativos:.1%} tiene un índice negativo: en
    esos píxeles el DN del rojo supera al del NIR.
    """
)
```
