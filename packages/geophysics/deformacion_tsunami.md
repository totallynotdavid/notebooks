```python hidden
from pathlib import Path

import contourpy
import numpy as np
from quire import md
from quire import plot as P
from tsunamis import legacy, mansinha, okada
from tsunamis.faults import (
    InversionFormat,
    fault_plane,
    local_xy,
    metres_per_degree,
    papazachos_scaling,
    subfaults_from_inversion,
    to_local,
)
from tsunamis.grid import read_grid
from tsunamis.kajiura import kajiura_filter

DATOS = Path(__file__).resolve().parent / "data"


def tabla(encabezado, filas):
    """Tabla Markdown con la primera columna a la izquierda y el resto a la derecha."""
    return md(
        "\n".join(
            [
                "| " + " | ".join(encabezado) + " |",
                "| --- |" + " ---: |" * (len(encabezado) - 1),
                *("| " + " | ".join(map(str, fila)) + " |" for fila in filas),
            ]
        )
    )


def campo(valores, x, y, paso, decimales=2, **opciones):
    """Raster de un campo (filas en y creciente) con una celda de cada `paso`.

    El navegador suaviza la imagen al escalarla, así que un campo suave se ve
    continuo aunque se envíe una muestra gruesa.
    """
    muestra = valores[::paso, ::paso]
    xs, ys = x[::paso], y[::paso]
    dx, dy = (xs[1] - xs[0]) / 2, (ys[1] - ys[0]) / 2
    return P.raster(
        fill=np.round(muestra, decimales).ravel(),
        width=muestra.shape[1],
        height=muestra.shape[0],
        x1=xs[0] - dx,
        x2=xs[-1] + dx,
        y1=ys[0] - dy,
        y2=ys[-1] + dy,
        **opciones,
    )


def curvas(x, y, valores, nivel, paso=3):
    """Curvas de nivel como una sola polilínea, cortada con NaN entre tramos."""
    muestra = valores[::paso, ::paso]
    tramos = contourpy.contour_generator(x[::paso], y[::paso], muestra).lines(nivel)
    nan = np.full((1, 2), np.nan)
    return np.concatenate([p for t in tramos for p in (t, nan)])


def divergente(limite, etiqueta, esquema="RdBu"):
    return {
        "type": "linear",
        "scheme": esquema,
        "reverse": esquema == "RdBu",
        "domain": [-limite, limite],
        "legend": True,
        "label": etiqueta,
    }
```

# De la falla al tsunami: deformación de Okada y filtro de Kajiura

Un terremoto de subducción levanta y hunde el fondo marino en segundos. Ese
movimiento empuja la columna de agua y da la condición inicial del tsunami. El
artículo calcula las dos cosas para el terremoto de Pisco de 2007 con el paquete
`tsunamis`, que reúne en Python los programas en Fortran y MATLAB de los
laboratorios del curso _Tópicos avanzados en tsunamis_:

1. el modelo de Okada para la deformación vertical del fondo (`def_oka.f`, de
   Koshimura, modificado por C. Jiménez), vectorizado sobre la grilla con NumPy;
2. una comprobación cruzada con el modelo de Mansinha y Smylie (`deform.f`);
3. la geometría de la falla y sus subfallas (`fault_plane_n.m`, `falla.m` y
   `fuji2oka.m`);
4. la batimetría GEBCO leída con sus coordenadas;
5. el filtro de Kajiura, que lleva la deformación del fondo a la elevación
   inicial de la superficie del mar.

## Validación contra el programa en Fortran

```python
pfalla = legacy.read_pfalla(DATOS / "pfalla.inp")
referencia = np.loadtxt(DATOS / "deform_a.grd")
calculada = legacy.run_def_oka(pfalla)
```

```python hidden
_, _, deslizamiento, largo, ancho, rumbo, buzamiento, desliz_angulo, tope = pfalla[0]
md(
    f"""
    El laboratorio 2 guarda `deform_a.grd`, la salida de `def_oka.f` para la
    falla de `pfalla.inp`: una subfalla de {largo / 1e3:.0f} × {ancho / 1e3:.0f}
    km, rumbo (strike) {rumbo:.0f}°, buzamiento (dip) {buzamiento:.0f}°, ángulo
    de deslizamiento (rake) {desliz_angulo:.0f}° y {deslizamiento:.0f} m de
    deslizamiento, con el borde superior a {tope / 1e3:.0f} km de profundidad.
    `run_def_oka` repite el cálculo en la misma ventana de
    {referencia.shape[0]} × {referencia.shape[1]} celdas, con el mismo tamaño
    de celda ({legacy.DX} m), y la comparación se hace celda por celda.
    """
)
```

```python hidden
diferencia = calculada - referencia
fuertes = np.abs(referencia) >= 0.1
i_max, j_max = np.unravel_index(np.abs(diferencia).argmax(), diferencia.shape)
tabla(
    ["", "valor"],
    [
        ["celdas comparadas", f"{referencia.shape[0]} × {referencia.shape[1]}"],
        [
            "rango de la referencia",
            f"{referencia.min():.3f} a {referencia.max():.3f} m",
        ],
        ["rango de la calculada", f"{calculada.min():.5f} a {calculada.max():.5f} m"],
        [
            "**diferencia absoluta máxima**",
            f"**{np.abs(diferencia).max():.1e} m** (celda {i_max}, {j_max})",
        ],
        [
            "relativa al máximo de la referencia",
            f"{np.abs(diferencia).max() / np.abs(referencia).max():.1e}",
        ],
        [
            "relativa máxima donde \\|referencia\\| ≥ 0.1 m",
            f"{(np.abs(diferencia[fuertes]) / np.abs(referencia[fuertes])).max():.1e}",
        ],
    ],
)
```

`deform_a.grd` se escribió con formato `F7.3`, así que cada dato ya lleva un
redondeo de hasta 5 × 10⁻⁴ m, y `def_oka.f` trabaja en precisión simple. La
diferencia máxima es de ese orden. La diferencia relativa punto a punto solo
tiene sentido donde la deformación es apreciable; cerca de cero domina el
redondeo del archivo.

```python hidden
celdas_i = np.arange(referencia.shape[0])
celdas_j = np.arange(referencia.shape[1])
conteo, bordes = np.histogram(diferencia.ravel() * 1e3, bins=60)
hay = conteo > 0
P.grid(
    P.figure(
        campo(referencia.T, celdas_i, celdas_j, 6),
        title="deform_a.grd (Fortran)",
        color=divergente(1.3, "uz (m)"),
        x={"label": "celda i (este)"},
        y={"label": "celda j (norte)"},
        aspectRatio=1,
        width=420,
        digits=3,
    ),
    P.figure(
        P.rectY(
            x1=bordes[:-1][hay],
            x2=bordes[1:][hay],
            y1=np.full(hay.sum(), 0.5),
            y2=conteo[hay],
            fill="currentColor",
            fillOpacity=0.6,
            tip=False,
        ),
        title="NumPy − Fortran",
        x={"label": "diferencia (mm)"},
        y={"type": "log", "label": "celdas", "grid": True, "nice": True},
        width=420,
    ),
)
```

```python hidden
md(
    f"""
    **Una inconsistencia del laboratorio original.** `def_oka.f` fija el tamaño
    de celda en {legacy.DX} m (30″), pero `grid_a.grd` del laboratorio 2 tenía
    celdas de 15″ (≈ 463 m). La ventana de {referencia.shape[0]} ×
    {referencia.shape[1]} celdas se había dimensionado para 15″, de modo que
    `deform_a.grd` quedaba dibujada al doble de escala respecto a la
    batimetría. Para reproducir el archivo hay que conservar esa convención; el
    resto del artículo usa coordenadas geográficas reales.
    """
)
```

## Comprobación cruzada: Okada y Mansinha–Smylie

`deform.f` implementa el modelo de Mansinha y Smylie, que supone un sólido de
Poisson (μ = λ). El modelo de Okada del paquete usa las velocidades de la
corteza de `def_oka.f`. Para la misma falla rectangular se esperan campos casi
idénticos.

```python
falla_ref = okada.Subfault(
    0.0, 0.0, largo, ancho, tope, rumbo, buzamiento, desliz_angulo, deslizamiento
)
x = np.linspace(-250e3, 250e3, 251)
y = np.linspace(-150e3, 300e3, 226)
xx, yy = np.meshgrid(x, y)
uz_okada = okada.vertical_displacement(xx, yy, [falla_ref])
uz_poisson = okada.vertical_displacement(xx, yy, [falla_ref], ratio=0.5)
uz_ms = mansinha.vertical_displacement(xx, yy, falla_ref)
```

```python hidden
# Perfil perpendicular al rumbo que pasa por el centro de la falla.
az = np.radians(rumbo + 90.0)
cx = 0.5 * largo * np.sin(np.radians(rumbo)) + 0.5 * ancho * np.cos(
    np.radians(buzamiento)
) * np.sin(az)
cy = 0.5 * largo * np.cos(np.radians(rumbo)) + 0.5 * ancho * np.cos(
    np.radians(buzamiento)
) * np.cos(az)
s = np.linspace(-150e3, 250e3, 401)
px, py = cx + s * np.sin(az), cy + s * np.cos(az)
P.grid(
    P.figure(
        campo(uz_okada, x / 1e3, y / 1e3, 3),
        P.line(
            x=(cx + s[[0, -1]] * np.sin(az)) / 1e3,
            y=(cy + s[[0, -1]] * np.cos(az)) / 1e3,
            stroke="#222",
            strokeDasharray="4,3",
            tip=False,
        ),
        title="Okada (corteza de def_oka.f)",
        color=divergente(1.3, "uz (m)"),
        x={"label": "este (km)"},
        y={"label": "norte (km)"},
        aspectRatio=1,
        width=420,
        digits=3,
    ),
    P.figure(
        P.ruleY([0], stroke="currentColor", strokeOpacity=0.3),
        P.line(
            x=s / 1e3,
            y=okada.vertical_displacement(px, py, [falla_ref]),
            series="Okada",
        ),
        P.line(
            x=s / 1e3,
            y=mansinha.vertical_displacement(px, py, falla_ref),
            series="Mansinha–Smylie",
            strokeDasharray="5,4",
        ),
        title="Perfil a lo largo de la línea discontinua",
        x={"label": "distancia al centro, perpendicular al rumbo (km)"},
        y={"label": "uz (m)", "grid": True},
        width=420,
    ),
)
```

```python hidden
md(
    f"""
    El máximo de la deformación es {uz_okada.max():.2f} m. Los dos campos
    difieren como mucho en {np.abs(uz_okada - uz_ms).max():.1e} m con la corteza
    de `def_oka.f`, y en {np.abs(uz_poisson - uz_ms).max():.1e} m si Okada se
    evalúa con el sólido de Poisson, donde las dos formulaciones deben
    coincidir.
    """
)
```

## Geometría de la fuente

`falla.m` estima el tamaño de la ruptura a partir de la magnitud con las
relaciones de escala de Papazachos et al. (2004) para fallas inversas en zonas
de subducción, ajustadas para 6.7 ≤ Mw ≤ 9.2. El deslizamiento sale del momento
sísmico con una rigidez de 4 × 10¹⁰ N/m².

```python hidden
escalas = [(mw, papazachos_scaling(mw)) for mw in (7.0, 7.5, 8.0, 8.5, 9.0)]
tabla(
    ["Mw", "L (km)", "W (km)", "deslizamiento (m)", "M0 (N m)"],
    [
        [
            f"{mw:.1f}",
            f"{e.length_km:.0f}",
            f"{e.width_km:.0f}",
            f"{e.slip_m:.2f}",
            f"{e.moment_nm:.2e}",
        ]
        for mw, e in escalas
    ],
)
```

## El terremoto de Pisco de 2007: ocho subfallas

La guía del laboratorio 3 (`data/guia_laboratorio_3.pdf`, tabla I) describe la
fuente como ocho subfallas cuadradas de 45 km, cuatro a lo largo del rumbo y dos
a lo largo del buzamiento. Cada fila da la esquina inferior izquierda de la
subfalla, su profundidad y su deslizamiento. `subfaults_from_inversion`
convierte esa tabla a subfallas de Okada y trata la longitud de cada fila por
separado: `fuji2oka.m` preguntaba `if xo < 0` sobre el vector completo, y por
eso una tabla con longitudes de ambos signos se convertía igual en todas las
filas.

```python
subfallas = subfaults_from_inversion(
    np.loadtxt(DATOS / "pisco_2007.txt"), InversionFormat.FAULT
)
contornos = [
    fault_plane(
        f.lon,
        f.lat,
        length=f.length,
        width=f.width,
        depth=f.depth,
        strike=f.strike,
        dip=f.dip,
        rake=f.rake,
        slip=f.slip,
    ).outline
    for f in subfallas
]
```

```python hidden
area = sum(f.length * f.width for f in subfallas)
momento = 4.0e10 * sum(f.length * f.width * f.slip for f in subfallas)
mw_fuente = (np.log10(momento) - 9.1) / 1.5
primera = subfallas[0]
tabla(
    ["subfalla", "lon (°)", "lat (°)", "profundidad (km)", "deslizamiento (m)"],
    [
        [k + 1, f"{f.lon:.3f}", f"{f.lat:.3f}", f"{f.depth / 1e3:.2f}", f"{f.slip:.1f}"]
        for k, f in enumerate(subfallas)
    ],
)
```

```python hidden
md(
    f"""
    Todas tienen rumbo {primera.strike:.0f}°, buzamiento {primera.dip:.0f}° y
    ángulo de deslizamiento {primera.rake:.0f}°. El área total es
    {area / 1e6:.0f} km² y el momento, {momento:.2e} N m, equivalente a
    Mw {mw_fuente:.2f}.
    """
)
```

## Deformación del fondo marino

```python
grilla = read_grid(DATOS / "estudio.npz")
lon0, lat0 = float(grilla.lon.mean()), float(grilla.lat.mean())
este, norte = local_xy(*np.meshgrid(grilla.lon, grilla.lat), lon0, lat0)
uplift = okada.vertical_displacement(este, norte, to_local(subfallas, lon0, lat0))
```

```python hidden
mar = grilla.elevation < 0
md(
    f"""
    La grilla de estudio es un recorte de GEBCO ({grilla.source}) de
    {grilla.lon[0]:.2f}° a {grilla.lon[-1]:.2f}° de longitud y de
    {grilla.lat[0]:.2f}° a {grilla.lat[-1]:.2f}° de latitud, con celdas de 30″
    ({len(grilla.lon)} × {len(grilla.lat)}). Las coordenadas salen del
    encabezado del archivo original. La deformación se evalúa en cada celda; la
    costa es la curva de elevación 0 m y las líneas grises, las isóbatas de
    200, 2000, 4000 y 6000 m. Sobre el mar, el levantamiento máximo es de
    {uplift[mar].max():.2f} m y el descenso máximo, de {-uplift[mar].min():.2f} m.
    """
)
```

```python hidden
costa = curvas(grilla.lon, grilla.lat, grilla.elevation, 0)
isobatas = np.concatenate(
    [
        curvas(grilla.lon, grilla.lat, grilla.elevation, -h)
        for h in (200, 2000, 4000, 6000)
    ]
)
bordes_fallas = np.concatenate([np.vstack([c, [[np.nan, np.nan]]]) for c in contornos])
limite = float(np.abs(uplift).max())
aspecto = 1 / np.cos(np.radians(lat0))


def mapa(valores, titulo, color, paso=5, decimales=2, ancho_figura=640):
    return P.figure(
        campo(valores, grilla.lon, grilla.lat, paso, decimales),
        P.line(
            x=isobatas[:, 0],
            y=isobatas[:, 1],
            stroke="#555",
            strokeOpacity=0.35,
            strokeWidth=0.6,
            tip=False,
        ),
        # El fondo del mapa es claro en los dos temas: la costa va en gris oscuro.
        P.line(x=costa[:, 0], y=costa[:, 1], stroke="#222", tip=False),
        P.line(
            x=bordes_fallas[:, 0],
            y=bordes_fallas[:, 1],
            stroke="#1b7837",
            strokeWidth=1,
            tip=False,
        ),
        title=titulo,
        color=color,
        x={"label": "longitud (°)", "domain": [grilla.lon[0], grilla.lon[-1]]},
        y={"label": "latitud (°)", "domain": [grilla.lat[0], grilla.lat[-1]]},
        aspectRatio=aspecto,
        width=ancho_figura,
        digits=4,
    )


mapa(
    uplift,
    "Deformación vertical del fondo (Okada, 8 subfallas)",
    divergente(limite, "uz (m)"),
)
```

## Del fondo a la superficie: el filtro de Kajiura

El mar no copia una deformación súbita del fondo. Para un océano incompresible
de profundidad $h$, la transformada de Fourier de la elevación inicial de la
superficie es la del levantamiento dividida por $\cosh(kh)$, con $k$ el número
de onda. Las longitudes de onda grandes frente a la profundidad pasan casi sin
cambio; las cortas se atenúan. Como $h$ varía, el filtro se aplica a varios
niveles de profundidad y cada celda toma el campo interpolado a su profundidad
local. Sobre tierra no se filtra.

Es una aproximación más simple que la de Abbate et al. (2024, _Natural Hazards
and Earth System Sciences_ 24, 2773), que escriben el filtro de Kajiura para un
fondo que se levanta de forma súbita y lo evalúan celda por celda con la
profundidad local. Aquí solo se interpola entre campos filtrados con profundidad
constante.

```python
lon_m, lat_m = metres_per_degree(lat0)
paso_x = lon_m * float(np.diff(grilla.lon).mean())
paso_y = lat_m * float(np.diff(grilla.lat).mean())
condicion_inicial = kajiura_filter(uplift, grilla.depth, paso_x, paso_y)
```

```python hidden
cambio = (condicion_inicial - uplift) * 100
P.grid(
    mapa(
        condicion_inicial,
        "Condición inicial (Kajiura)",
        divergente(limite, "η (m)"),
        ancho_figura=420,
    ),
    mapa(
        cambio,
        "Kajiura − fondo",
        divergente(float(np.abs(cambio).max()), "cm", "PuOr"),
        decimales=1,
        ancho_figura=420,
    ),
)
```

## Perfil perpendicular a la falla

```python hidden
azimut = (primera.strike + 90.0) % 360.0
centro_x, centro_y = local_xy(
    *np.mean([c[:4] for c in contornos], axis=(0, 1)), lon0, lat0
)
distancia = np.arange(-120e3, 260e3, 500.0)
px = centro_x + distancia * np.sin(np.radians(azimut))
py = centro_y + distancia * np.cos(np.radians(azimut))
dentro = (
    (px >= este[0, 0])
    & (px <= este[0, -1])
    & (py >= norte[0, 0])
    & (py <= norte[-1, 0])
)
distancia, px, py = distancia[dentro], px[dentro], py[dentro]
# Índices fraccionarios: la grilla es regular en este y en norte.
col = (px - este[0, 0]) / (este[0, 1] - este[0, 0])
fila = (py - norte[0, 0]) / (norte[1, 0] - norte[0, 0])
c0 = np.minimum(col.astype(int), este.shape[1] - 2)
f0 = np.minimum(fila.astype(int), este.shape[0] - 2)
tc, tf = col - c0, fila - f0


def en_perfil(valores):
    """Interpolación bilineal del campo en los puntos del perfil."""
    abajo = valores[f0, c0] * (1 - tc) + valores[f0, c0 + 1] * tc
    arriba = valores[f0 + 1, c0] * (1 - tc) + valores[f0 + 1, c0 + 1] * tc
    return abajo * (1 - tf) + arriba * tf


km = distancia / 1e3
z = en_perfil(grilla.elevation)
costa_km = km[np.flatnonzero(np.diff(np.sign(z)))[0]]
dominio = [km[0], km[-1]]
md(
    f"""
    El perfil pasa por el centro de la fuente en la dirección del buzamiento
    (azimut rumbo + 90° = {azimut:.0f}°). La línea vertical punteada marca la
    costa, a {costa_km:.0f} km del centro hacia tierra. El levantamiento
    máximo del perfil está a {km[en_perfil(uplift).argmax()]:.0f} km, en el
    mar.
    """
)
```

```python hidden
costa_marca = P.ruleX([costa_km], stroke="#d62728", strokeDasharray="2,3")
P.figure(
    P.areaY(
        x=km,
        y1=np.full(len(z), z.min()),
        y2=z,
        fill="currentColor",
        fillOpacity=0.12,
        tip=False,
    ),
    P.line(x=km, y=z, stroke="currentColor"),
    P.ruleY([0], stroke="currentColor", strokeOpacity=0.5),
    costa_marca,
    title="Batimetría y topografía",
    x={"label": None, "domain": dominio},
    y={"label": "elevación (m)", "grid": True},
    height=200,
)
```

```python hidden
P.figure(
    P.ruleY([0], stroke="currentColor", strokeOpacity=0.3),
    P.line(x=km, y=en_perfil(uplift), series="deformación del fondo"),
    P.line(
        x=km,
        y=en_perfil(condicion_inicial),
        series="condición inicial (Kajiura)",
        strokeDasharray="5,4",
    ),
    costa_marca,
    x={"label": None, "domain": dominio},
    y={"label": "m", "grid": True},
    height=240,
)
```

```python hidden
P.figure(
    P.ruleY([0], stroke="currentColor", strokeOpacity=0.3),
    P.line(x=km, y=en_perfil(cambio), stroke="#d62728"),
    costa_marca,
    x={
        "label": f"distancia al centro de la fuente, azimut {azimut:.0f}° (km)",
        "domain": dominio,
    },
    y={"label": "Kajiura − fondo (cm)", "grid": True},
    height=180,
)
```

```python hidden
profundidad_fuente = grilla.depth[mar & (np.abs(uplift) > 0.1)].max()
md(
    f"""
    Sobre el mar, la condición inicial filtrada llega a
    {condicion_inicial[mar].max():.3f} m y {condicion_inicial[mar].min():.3f} m,
    los mismos extremos que el fondo ({uplift[mar].max():.3f} m y
    {uplift[mar].min():.3f} m). Las subfallas miden 45 km y donde el fondo se mueve más de 10 cm el agua
    no pasa de {profundidad_fuente / 1e3:.1f} km de profundidad. La longitud de
    onda de la deformación es mucho mayor que la profundidad ($kh \\ll 1$) y el
    filtro cambia poco el campo. La
    diferencia llega a {np.abs(cambio[mar]).max():.0f} cm y se concentra en los
    bordes de la ruptura, donde el levantamiento cambia más rápido. El filtro
    pesa más con fuentes pequeñas o aguas profundas. Esta elevación es la
    condición inicial que un modelo de propagación, por ejemplo de aguas
    someras lineales, recibiría para seguir el tsunami hasta la costa.
    """
)
```
