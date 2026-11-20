```python hidden
import tempfile
from datetime import timedelta
from pathlib import Path
from xml.dom import minidom
from types import SimpleNamespace

import numpy as np
from correction import (
    BIAS,
    GAIN,
    XML_PATH,
    _sixs,
    load_clip,
    load_inputs,
    load_metadata,
    run_correction,
)
from gf1pms import BANDS
from Py6S import AtmosCorr, Wavelength
from quire import cache, md
from quire import plot as P
from quire import table as tabla

# Py6S borra la entrada temporal al terminar cada corrida. Usa el directorio
# del artículo para no escribir en el directorio temporal del sistema.
tempfile.tempdir = str(Path(__file__).resolve().parent)


def colores(rgb, bajo, alto):
    """Colores hexadecimales de una imagen (3, filas, columnas) estirada entre bajo y alto."""
    escala = np.clip((rgb - bajo) / (alto - bajo), 0, 1)
    niveles = np.round(np.nan_to_num(escala) * 255).astype(int).reshape(3, -1)
    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in niveles.T]
```

# Corrección atmosférica de una imagen GaoFen-1 con 6S

El sensor PMS del satélite chino GaoFen-1 mide cuatro bandas multiespectrales:
azul, verde, rojo e infrarrojo cercano (NIR). Lo que mide es la radiancia en el
techo de la atmósfera, que mezcla la luz reflejada por la superficie con la que
la atmósfera dispersa hacia el sensor. La corrección atmosférica estima la
reflectancia de la superficie quitando ese aporte con el modelo 6S.

El artículo usa un recorte de 512 × 512 píxeles de una escena GF-1D sobre la
Amazonía peruana, cerca de Iquitos. La escena completa está en una carpeta de
Google Drive; `prepare.py` la descarga, recorta el clip y consulta en Earth
Engine los datos atmosféricos de la fecha.

## La escena

```python
sensor, perfil = load_clip()
metadata = load_metadata()
entradas = load_inputs()
valores = entradas["values"]
```

```python hidden
def hora_solar(utc):
    """Hora solar media en la longitud del centro de la escena."""
    local = utc + timedelta(hours=metadata["longitude"] / 15)
    return f"{local:%H:%M}"


md(
    f"""
    - Adquisición: {metadata["date"]:%Y-%m-%d %H:%M} UTC. El archivo XML da la
      hora de China (UTC+8), que se convierte a UTC para 6S y Earth Engine.
      Así la hora solar media en la escena es {hora_solar(metadata["date"])};
      leída como UTC sería {hora_solar(metadata["date"] + timedelta(hours=8))},
      y el sol no estaría a {metadata["solar_zenith"]:.0f}° del cenit.
    - Centro de la escena: {abs(metadata["latitude"]):.3f}° S,
      {abs(metadata["longitude"]):.3f}° O.
    - Recorte: {sensor.shape[2]} × {sensor.shape[1]} píxeles de
      {perfil["transform"].a:.0f} m, en `{perfil["crs"]}`.
    - Ángulo cenital solar: {metadata["solar_zenith"]:.1f}°. Ángulo cenital
      de observación: {metadata["view_zenith"]:.1f}°.
    """
)
```

## Calibración radiométrica

Cada píxel guarda un número digital (DN). El Centro de Satélites de Recursos de
China (CRESDA) publica cada año, por satélite y banda, una ganancia $g$ y un
desplazamiento que llevan el DN a radiancia en W m⁻² sr⁻¹ µm⁻¹: $L = g \cdot
\mathrm{DN} + \text{desplazamiento}$. Para el PMS de GF-1D el desplazamiento
es 0. Cada fila de la tabla de CRESDA vale para un modo de ganancia y un nivel
de integración, y la que se usa debe coincidir con los del producto.

```python hidden
xml = minidom.parse(str(XML_PATH))


def campo(nombre):
    return xml.getElementsByTagName(nombre)[0].firstChild.data.strip()


md(
    f"""
    El XML de esta escena da los modos de ganancia `{campo("GainMode")}` y los
    niveles de integración `{campo("IntegrationLevel")}`, banda por banda. En
    las tablas 2 a 5 del archivo `GF1D.docx` de CRESDA (anexo 2, coeficientes
    históricos de 2008 a 2025) coinciden con la segunda fila de 2020, la del
    día 847 tras la puesta en órbita. Sus ganancias son las de
    `correction.py`.
    """
)
```

Tres errores cambian el resultado sin dar ningún aviso: dividir el DN entre la
ganancia en lugar de multiplicarlo, usar los coeficientes de GF-1 en una escena
de GF-1D y tomar la hora del XML como UTC.

```python hidden
NOMBRES = ["azul", "verde", "rojo", "NIR"]
tabla(
    ["banda", "intervalo (µm)", "ganancia", "DN mediano"],
    [
        [
            nombre,
            f"{BANDS[f'B{i + 1}'][0]:.3f}–{BANDS[f'B{i + 1}'][1]:.3f}",
            f"{GAIN[i]:.4f}",
            f"{np.median(sensor[i]):.0f}",
        ]
        for i, nombre in enumerate(NOMBRES)
    ],
)
```

## La atmósfera de ese día

6S necesita el estado de la atmósfera sobre la escena. `prepare.py` lo toma de
Earth Engine en el centro de la escena y a la hora de adquisición:

```python hidden
fuentes = entradas["datasets"]
tabla(
    ["variable", "valor", "conjunto de Earth Engine"],
    [
        ["elevación (km)", valores["elevation_km"], f"`{fuentes['elevation']}`"],
        [
            "vapor de agua (g/cm²)",
            f"{valores['water_vapour_g_cm2']:.2f}",
            f"`{fuentes['water_vapour']}`",
        ],
        ["ozono (cm-atm)", valores["ozone_atm_cm"], f"`{fuentes['ozone']}`"],
        [
            "AOD a 550 nm",
            valores["aerosol_optical_depth_550"],
            f"`{fuentes['aerosol']}`",
        ],
    ],
)
```

## Corrección con 6S

6S se ejecuta una vez por banda, con la respuesta espectral del sensor. De cada
corrida salen la radiancia de trayecto $L_p$ (luz que la atmósfera dispersa
hacia el sensor), las transmitancias de subida por gases $T_g$ y por dispersión
$T_s$, y la irradiancia directa y difusa en el suelo, $E_\mathrm{dir}$ y
$E_\mathrm{dif}$. La reflectancia de la superficie es

$$\rho = \frac{\pi \, (L - L_p)}{T_g \, T_s \, (E_\mathrm{dir} + E_\mathrm{dif})}$$

La fórmula supone una superficie lambertiana y omite la luz que rebota entre el
suelo y la atmósfera. La inversión lambertiana del propio 6S sí la incluye, con
el albedo esférico $S$ de la atmósfera: calcula $y = x_a L - x_b$ y da $\rho = y
/ (1 + S\,y)$, con coeficientes $x_a$ y $x_b$ que salen de la misma corrida.

```python
@cache
def coeficientes_6s(banda, metadata, valores):
    sixs = _sixs(metadata, {"values": valores})
    sixs.wavelength = Wavelength(*BANDS[banda])
    sixs.run()
    o = sixs.outputs
    return SimpleNamespace(
        trayecto=o.atmospheric_intrinsic_radiance,
        gases=o.trans["global_gas"].upward,
        dispersion=o.trans["total_scattering"].upward,
        irradiancia=o.direct_solar_irradiance + o.diffuse_solar_irradiance,
        # Factor que lleva la radiancia a reflectancia en el techo de la atmósfera.
        a_toa=o.apparent_reflectance / o.apparent_radiance,
    )


coeficientes = [coeficientes_6s(f"B{i + 1}", metadata, valores) for i in range(4)]
reflectancia = run_correction(sensor, metadata, entradas)
```

```python hidden
radiancia = sensor.astype(float) * GAIN[:, None, None] + BIAS[:, None, None]
fraccion = [
    c.trayecto / float(np.median(radiancia[i])) for i, c in enumerate(coeficientes)
]
tabla(
    [
        "banda",
        "L mediana",
        "L_p",
        "L_p / L",
        "T_g T_s",
        "E_dir + E_dif (W m⁻² µm⁻¹)",
    ],
    [
        [
            nombre,
            f"{np.median(radiancia[i]):.1f}",
            f"{c.trayecto:.1f}",
            f"{fraccion[i]:.0%}",
            f"{c.gases * c.dispersion:.3f}",
            f"{c.irradiancia:.0f}",
        ]
        for i, (nombre, c) in enumerate(zip(NOMBRES, coeficientes, strict=True))
    ],
)
```

```python hidden
md(
    f"""
    Las radiancias están en W m⁻² sr⁻¹ µm⁻¹. En el azul, la radiancia de
    trayecto es el {fraccion[0]:.0%} de la radiancia mediana que mide el
    sensor: es luz dispersada por la atmósfera, no reflejada por el bosque. En
    el NIR la fracción baja al {fraccion[3]:.0%}: la radiancia de trayecto cae
    de {coeficientes[0].trayecto:.1f} a {coeficientes[3].trayecto:.1f} y la
    radiancia medida sube a {np.median(radiancia[3]):.1f}.
    """
)
```

```python hidden
@cache
def inversion_6s(banda, radiancia_mediana, metadata, valores):
    sixs = _sixs(metadata, {"values": valores})
    sixs.wavelength = Wavelength(*BANDS[banda])
    sixs.atmos_corr = AtmosCorr.AtmosCorrLambertianFromRadiance(radiancia_mediana)
    sixs.run()
    o = sixs.outputs
    y = o.coef_xa * radiancia_mediana - o.coef_xb
    return y / (1 + o.coef_xc * y)


def formula(i):
    c = coeficientes[i]
    L = float(np.median(radiancia[i]))
    return np.pi * (L - c.trayecto) / (c.gases * c.dispersion * c.irradiancia)


propia = [
    inversion_6s(f"B{i + 1}", float(np.median(radiancia[i])), metadata, valores)
    for i in range(4)
]
md(
    f"""
    En el píxel de radiancia mediana, la fórmula y la inversión de 6S dan
    {"; ".join(f"{formula(i):.4f} y {propia[i]:.4f} en el {n}" for i, n in enumerate(NOMBRES))}.
    En el NIR, la banda de mayor reflectancia, la fórmula da un
    {formula(3) / propia[3] - 1:.0%} más que 6S.
    """
)
```

## Reflectancia de la superficie

```python hidden
tabla(
    ["banda", "media", "mediana", "máximo"],
    [
        [
            nombre,
            f"{np.nanmean(reflectancia[i]):.3f}",
            f"{np.nanmedian(reflectancia[i]):.3f}",
            f"{np.nanmax(reflectancia[i]):.3f}",
        ]
        for i, nombre in enumerate(NOMBRES)
    ],
)
```

```python hidden
toa = radiancia * np.array([c.a_toa for c in coeficientes])[:, None, None]


def mediana_rgb(imagen):
    return ", ".join(f"{float(np.nanmedian(imagen[i])):.3f}" for i in (2, 1, 0))


md(
    f"""
    Para comparar antes y después hace falta la misma magnitud en las dos
    imágenes. 6S da el factor que lleva la radiancia a reflectancia en el techo
    de la atmósfera (TOA). En el azul, la reflectancia mediana es
    {np.median(toa[0]):.3f} en el TOA y {np.nanmedian(reflectancia[0]):.3f} en
    la superficie. Las dos composiciones en color verdadero usan la misma
    escala, de 0 a 0.15, y muestran un píxel de cada cuatro. Las medianas de
    rojo, verde y azul son {mediana_rgb(toa)} en el TOA, donde domina el azul
    que dispersa la atmósfera, y {mediana_rgb(reflectancia)} en la superficie,
    donde domina el verde.
    """
)
```

```python hidden
paso = 4
alto, ancho = sensor.shape[1] // paso, sensor.shape[2] // paso


def composicion(imagen, titulo):
    rgb = imagen[[2, 1, 0], ::paso, ::paso].astype(float)
    return P.figure(
        P.raster(
            fill=colores(rgb, 0.0, 0.15),
            width=ancho,
            height=alto,
            x1=0,
            y1=0,
            x2=sensor.shape[2],
            y2=sensor.shape[1],
            imageRendering="pixelated",
        ),
        title=titulo,
        x={"axis": None},
        y={"axis": None, "domain": [sensor.shape[1], 0]},
        aspectRatio=1,
        width=420,
    )


P.grid(
    composicion(toa, "Reflectancia en el techo de la atmósfera"),
    composicion(reflectancia, "Reflectancia de la superficie (6S)"),
)
```

## NDVI

Con la reflectancia corregida el NDVI ya es una magnitud física de la
superficie:

```python
ndvi = (reflectancia[3] - reflectancia[2]) / (reflectancia[3] + reflectancia[2])
```

```python hidden
P.figure(
    P.raster(
        fill=ndvi[::paso, ::paso].ravel(),
        width=ancho,
        height=alto,
        x1=0,
        y1=0,
        x2=sensor.shape[2],
        y2=sensor.shape[1],
        imageRendering="pixelated",
    ),
    title="NDVI de la reflectancia corregida",
    color={"scheme": "BrBG", "domain": [-1, 1], "legend": True, "label": "NDVI"},
    x={"axis": None},
    y={"axis": None, "domain": [sensor.shape[1], 0]},
    aspectRatio=1,
    width=480,
    digits=2,
)
```

```python hidden
rio = ndvi < 0.2
md(
    f"""
    La mediana del NDVI es {float(np.nanmedian(ndvi)):.2f} y el
    {float(np.nanmean(ndvi > 0.6)):.0%} de los píxeles supera 0.6. Los píxeles
    con NDVI menor que 0.2 son el
    {float(rio.mean()):.0%} del recorte. Su NDVI mediano es
    {round(float(np.nanmedian(ndvi[rio])), 2) + 0.0:.2f}: reflejan casi lo mismo en el rojo
    ({float(np.nanmedian(reflectancia[2][rio])):.2f}) que en el NIR
    ({float(np.nanmedian(reflectancia[3][rio])):.2f}).
    """
)
```
