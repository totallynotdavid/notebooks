```python hidden
from pathlib import Path

import contourpy
import numpy as np
from quire import md
from quire import plot as P
from quire import table as tabla
from tsunamis import mansinha, okada
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

# Condición inicial de un tsunami

Un terremoto de subducción levanta y hunde el fondo marino en segundos. Ese
movimiento empuja la columna de agua y da la condición inicial del tsunami. El
artículo la calcula para el terremoto de Pisco de 2007 en tres pasos:

1. la deformación vertical del fondo con el modelo de Okada (1985), comprobado
   contra el de Mansinha y Smylie (1971);
2. la fuente de Pisco como ocho subfallas sobre la batimetría GEBCO;
3. el filtro de Kajiura, que lleva la deformación del fondo a la superficie del
   mar.

## Okada y Mansinha–Smylie

Los dos modelos dan el desplazamiento de la superficie de un semiespacio
elástico cuando una falla rectangular desliza. Mansinha y Smylie suponen un
sólido de Poisson (λ = μ). Okada admite cualquier relación entre las constantes
elásticas. Con la misma falla se esperan campos casi idénticos.

```python
largo, ancho, tope = 160e3, 70e3, 5e3
rumbo, buzamiento, desliz_angulo, deslizamiento = 310.0, 18.0, 63.0, 3.0
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
md(
    f"""
    La falla de prueba mide {largo / 1e3:.0f} × {ancho / 1e3:.0f} km, con rumbo
    (strike) {rumbo:.0f}°, buzamiento (dip) {buzamiento:.0f}°, ángulo de
    deslizamiento (rake) {desliz_angulo:.0f}°, {deslizamiento:.0f} m de
    deslizamiento y el borde superior a {tope / 1e3:.0f} km de profundidad.
    Okada usa una corteza con ondas P de {okada.VP / 1e3:.2f} km/s y ondas S de
    {okada.VS / 1e3:.2f} km/s.
    """
)
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
        title="Okada",
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
    difieren como mucho en {np.abs(uz_okada - uz_ms).max():.1e} m con esa
    corteza, y en {np.abs(uz_poisson - uz_ms).max():.1e} m si Okada se evalúa
    con el sólido de Poisson, donde las dos formulaciones deben coincidir.
    """
)
```

## Tamaño de la ruptura

Las relaciones de escala de Papazachos et al. (2004) para fallas inversas en
zonas de subducción dan el largo y el ancho de la ruptura a partir de la
magnitud, para 6.7 ≤ Mw ≤ 9.2. El deslizamiento sale del momento sísmico con una
rigidez de 4 × 10¹⁰ N/m².

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

## El terremoto de Pisco de 2007

Jiménez et al. (2012) obtuvieron la fuente por inversión de mareogramas: ocho
subfallas cuadradas de 45 km, cuatro a lo largo del rumbo y dos a lo largo del
buzamiento, cada una con su propio deslizamiento.

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
    ({len(grilla.lon)} × {len(grilla.lat)}). La deformación se evalúa en cada celda; la
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

Es una aproximación más simple que la de Abbate et al. (2024), que escriben el
filtro de Kajiura para un fondo que se levanta de forma súbita y lo evalúan
celda por celda con la profundidad local. Aquí solo se interpola entre campos
filtrados con profundidad constante.

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

## Referencias

- Abbate, A., et al. (2024). Modelling tsunami initial conditions due to rapid
  coseismic seafloor displacement: efficient numerical integration and a tool to
  build unit source databases. _Natural Hazards and Earth System Sciences_ 24,
  2773–2791.
- Jiménez, C., Moggiano, N. y Saavedra, M. (2012). Fuente sísmica del terremoto
  de Pisco 2007 a partir de inversión de registros mareográficos. _Revista de
  Investigación de Física_ 15(2), 1–8.
- Mansinha, L. y Smylie, D. E. (1971). The displacement fields of inclined
  faults. _Bulletin of the Seismological Society of America_ 61(5), 1433–1440.
- Okada, Y. (1985). Surface deformation due to shear and tensile faults in a
  half-space. _Bulletin of the Seismological Society of America_ 75(4),
  1135–1154.
- Papazachos, B. C., et al. (2004). Global relations between seismic fault
  parameters and moment magnitude of earthquakes. _Bulletin of the Geological
  Society of Greece_ 36, 1482–1489.
