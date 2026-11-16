```python hidden
import warnings
from pathlib import Path

import numpy as np
from obspy import UTCDateTime, read
from obspy.signal.trigger import classic_sta_lta
from obspy.taup import TauPyModel
from quire import md
from quire import plot as P

# ObsPy redondea el delta de precisión simple de SAC y emite esta advertencia.
warnings.filterwarnings("ignore", message="Sample spacing read from SAC file")

DATOS = Path(__file__).resolve().parent / "data" / "sac"


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


def etiqueta(tr):
    return f"{tr.stats.network}.{tr.stats.station}"


def tiempo_desde_origen(tr):
    # times() cuenta desde el inicio del registro; O y B son relativos a la
    # misma hora de referencia.
    return tr.times() + tr.stats.sac.b - tr.stats.sac.o
```

# Procesamiento de señales sísmicas con ObsPy

Registros de la componente vertical (BHZ) del terremoto de Pisco del 15 de
agosto de 2007 (Mw 8.0), en formato SAC. El artículo lee los archivos, quita la
tendencia, filtra, ordena los registros por distancia, pica la llegada de la
onda P con un detector STA/LTA y calcula espectros. Todo se calcula al construir
la página a partir de los archivos de `data/sac/`.

## Los datos

```python
# IU.TUC..._filtered.SAC es una salida de SAC (rmean, trans, bp, int), no un
# registro crudo, y repetiría la estación.
archivos = sorted(p for p in DATOS.glob("*.SAC") if not p.stem.endswith("_filtered"))
trazas = [read(p, format="SAC")[0] for p in archivos]

# El centro de datos escribió el tiempo origen del evento como O, en segundos
# desde la hora de referencia de cada archivo.
origenes = np.array([(tr.stats.starttime + tr.stats.sac.o).timestamp for tr in trazas])
principal = np.abs(origenes - np.median(origenes)) < 60
```

```python hidden
origen_principal = UTCDateTime(round(float(np.median(origenes))))
otro_evento = [etiqueta(tr) for tr, p in zip(trazas, principal, strict=True) if not p]
otro_origen = UTCDateTime(round(float(origenes[~principal][0])))
profundidad = {bool(p): float(tr.stats.sac.evdp) for tr, p in zip(trazas, principal)}
por_etiqueta = {etiqueta(tr): tr for tr in trazas}
kip_g, kip_iu = por_etiqueta["G.KIP"].data, por_etiqueta["IU.KIP"].data
kip_igual = kip_g.size < kip_iu.size and np.array_equal(kip_g, kip_iu[: kip_g.size])
md(
    f"""
    Se leyeron **{len(trazas)} registros** BHZ:
    {", ".join(sorted(etiqueta(tr) for tr in trazas))}.

    **Un evento distinto.** Las cabeceras de {" y ".join(otro_evento)} fijan un
    origen en {otro_origen.strftime("%Y-%m-%d %H:%M:%S")} UTC y una
    profundidad de {profundidad[False]:.1f} km. Los otros
    {int(principal.sum())} registros fijan
    {origen_principal.strftime("%Y-%m-%d %H:%M:%S")} UTC y
    {profundidad[True]:.1f} km. Esas dos estaciones registraron otro
    terremoto, no el de Pisco. Se pican igual, pero no entran en la sección
    sísmica ni en los espectros.

    **Redes duplicadas.** KIP y SFJD aparecen en dos redes (G o GE, e IU) con
    la misma ubicación. Los dos registros de SFJD empiezan a horas distintas y
    sus muestras no coinciden.
    {"Las muestras de G.KIP son, una a una, las primeras de IU.KIP: es el mismo registro, cortado antes, y da el mismo pick." if kip_igual else "Los dos registros de KIP también difieren."}
    Cada registro se trata por separado.
    """
)
```

```python hidden
escalas = [float(tr.stats.sac.scale) for tr in trazas]
sensores = sorted({tr.stats.sac.kinst.strip().title() for tr in trazas})
md(
    f"""
    ## Amplitudes en cuentas

    La respuesta instrumental solo se puede quitar si se conoce. Las cabeceras
    SAC traen un factor `SCALE` por registro (entre {min(escalas):.2g} y
    {max(escalas):.2g}) y un texto de instrumento (`KINST`:
    {", ".join(sensores)}), pero no polos ni ceros, y el repositorio no tiene
    archivos `SACPZ` ni `RESP`. Sin eso no hay función de transferencia que
    deconvolucionar.

    **Todas las amplitudes del artículo están en cuentas del digitalizador.**
    Los instrumentos difieren entre estaciones, así que una amplitud en cuentas
    no se compara entre dos estaciones. Sí se comparan formas de onda, tiempos y
    contenido de frecuencias.
    """
)
```

## Preprocesamiento y sección sísmica

Cada registro se prepara así: se quita la tendencia lineal (esto incluye la
media), se aplica una ventana de coseno al 5 % de cada extremo para que el
filtro no vea un salto, y se filtra con un pasabanda Butterworth de 0.01 a 0.2
Hz (periodos de 5 a 100 s). El filtro es de fase cero: no desplaza la forma de
onda, pero deja energía antes de la llegada. Para picar la onda P más abajo se
usa otro filtro, causal.

```python
def preparar(tr, banda=(0.01, 0.2)):
    x = tr.copy()
    x.detrend("linear")
    x.taper(0.05)
    x.filter("bandpass", freqmin=banda[0], freqmax=banda[1], corners=5, zerophase=True)
    return x


seccion = sorted(
    (tr for tr, p in zip(trazas, principal, strict=True) if p),
    key=lambda tr: tr.stats.sac.gcarc,
)
```

La sección ordena las estaciones por distancia epicentral (campo `GCARC`) y
normaliza cada traza por su máximo. El tiempo se mide desde el origen del
terremoto. Tras el filtro no queda energía sobre 0.2 Hz, así que basta una
muestra cada 2 s.

```python hidden
tiempos, desplazadas, grupos = [], [], []
for i, tr in enumerate(seccion):
    x = preparar(tr)
    paso = round(2 * x.stats.sampling_rate)
    tiempos.append(tiempo_desde_origen(x)[::paso])
    desplazadas.append(i + 0.45 * x.data[::paso] / abs(x.data).max())
    grupos.append(np.full(tiempos[-1].size, i))
inicio = min(t[0] for t in tiempos)
P.figure(
    P.line(
        x=np.concatenate(tiempos),
        y=np.concatenate(desplazadas),
        z=np.concatenate(grupos),
        stroke="currentColor",
        strokeWidth=0.6,
        tip=False,
    ),
    P.text(
        x=[inicio] * len(seccion),
        y=list(range(len(seccion))),
        text=[f"{etiqueta(tr)} {tr.stats.sac.gcarc:.1f}°" for tr in seccion],
        textAnchor="end",
        dx=-8,
        fontSize=11,
    ),
    title="Pisco 2007, BHZ, pasabanda de 0.01 a 0.2 Hz, ordenado por distancia",
    x={"label": "tiempo desde el origen (s)"},
    y={"axis": None, "domain": [-1, len(seccion)]},
    marginLeft=130,
    height=640,
    grid=True,
    digits=4,
)
```

## Picado de la onda P con STA/LTA

El detector STA/LTA compara la energía de una ventana corta (STA) con la de una
ventana larga (LTA) que la precede. En el ruido el cociente ronda 1. Cuando
llega una señal, la ventana corta la ve antes y el cociente sube. La llegada es
la primera muestra en que el cociente supera un umbral.

Los parámetros son los mismos para todas las trazas:

- Filtro: pasabanda Butterworth causal de 1 a 3 Hz, de cuatro polos. Un filtro
  de fase cero adelantaría el pico.
- STA de 2 s, LTA de 20 s, umbral 3.
- La búsqueda empieza a los 40 s (el doble de la LTA). Antes la LTA no está
  llena y el transitorio del filtro dispara falsas alarmas.

Estos valores se escogieron probando varias combinaciones y se comparan abajo
con la referencia, así que el acuerdo no es una prueba ciega del método.

```python
BANDA_PICK = (1.0, 3.0)
STA, LTA, UMBRAL = 2.0, 20.0, 3.0


def picar_p(tr):
    x = tr.copy()
    x.detrend("linear")
    x.filter(
        "bandpass",
        freqmin=BANDA_PICK[0],
        freqmax=BANDA_PICK[1],
        corners=4,
        zerophase=False,
    )
    fs = x.stats.sampling_rate
    razon = classic_sta_lta(x.data, int(STA * fs), int(LTA * fs))
    inicio = int(2 * LTA * fs)
    sobre = np.flatnonzero(razon[inicio:] > UMBRAL)
    t = tiempo_desde_origen(x)
    pick = t[inicio + sobre[0]] if sobre.size else None
    return {"t": t, "senal": x.data, "razon": razon, "pick": pick}
```

La referencia es el tiempo teórico de la onda P en el modelo iasp91, con la
distancia y la profundidad de cada cabecera. `obspy.taup` trae el modelo y no
usa la red. Las cabeceras SAC también pueden guardar picks de analista en los
campos `A` y `T0` a `T9`.

```python
CAMPOS_PICK = ("a", *(f"t{i}" for i in range(10)))
modelo = TauPyModel("iasp91")


def p_teorica(tr):
    llegadas = modelo.get_travel_times(
        source_depth_in_km=float(tr.stats.sac.evdp),
        distance_in_degree=float(tr.stats.sac.gcarc),
        phase_list=["P"],
    )
    return llegadas[0].time


# Un pick a más de TOLERANCIA s de la P teórica se marca para revisión.
TOLERANCIA = 5.0
resultados = []
for tr in trazas:
    picado = picar_p(tr)
    teorica = p_teorica(tr)
    resultados.append(
        {
            "traza": tr,
            "picado": picado,
            "teorica": teorica,
            "dif": None if picado["pick"] is None else picado["pick"] - teorica,
            "cabecera": {c: tr.stats.sac[c] for c in CAMPOS_PICK if c in tr.stats.sac},
        }
    )
```

```python hidden
con_cabecera = [r for r in resultados if r["cabecera"]]
sin_pick = [etiqueta(r["traza"]) for r in resultados if r["dif"] is None]
buenos = np.array(
    [
        r["dif"]
        for r in resultados
        if r["dif"] is not None and abs(r["dif"]) <= TOLERANCIA
    ]
)
cabecera = (
    f"{len(con_cabecera)} registros tienen un pick de analista en la cabecera."
    if con_cabecera
    else "Ningún registro tiene picks de analista en la cabecera, así que la"
    " referencia es solo el tiempo teórico."
)
picados = (
    f"El detector pica los {len(resultados)} registros."
    if not sin_pick
    else f"El detector no pica {', '.join(sin_pick)}."
)
md(
    f"""
    ### Resultado

    {cabecera} {picados} {len(buenos)} picks quedan a menos de
    {TOLERANCIA:g} s de la onda P teórica, con una mediana de
    {np.median(buenos):+.1f} s: el detector llega tarde porque necesita que la
    ventana STA se llene de señal, y la onda P telesísmica empieza de forma
    gradual. Los otros {len(resultados) - len(buenos) - len(sin_pick)} quedan
    marcados "revisar". Los tiempos se miden desde el origen del terremoto de
    cada registro.
    """
)
```

```python hidden
def estado(r):
    if r["dif"] is None:
        return "sin pick"
    return "revisar" if abs(r["dif"]) > TOLERANCIA else "ok"


tabla(
    [
        "estación",
        "distancia (°)",
        "P teórica (s)",
        "P STA/LTA (s)",
        "diferencia (s)",
        "estado",
    ],
    [
        [
            etiqueta(r["traza"]) + ("" if p else " (otro evento)"),
            f"{r['traza'].stats.sac.gcarc:.1f}",
            f"{r['teorica']:.1f}",
            "" if r["dif"] is None else f"{r['picado']['pick']:.1f}",
            "" if r["dif"] is None else f"{r['dif']:+.1f}",
            estado(r),
        ]
        for r, p in zip(resultados, principal, strict=True)
    ],
)
```

```python hidden
def puntos(nombre, incluir):
    elegidos = [
        r
        for r, p in zip(resultados, principal, strict=True)
        if r["dif"] is not None and incluir(r, p)
    ]
    return P.dot(
        x=[r["traza"].stats.sac.gcarc for r in elegidos],
        y=[r["dif"] for r in elegidos],
        title=[etiqueta(r["traza"]) for r in elegidos],
        series=nombre,
        r=4,
    )


P.figure(
    P.rectY(
        [0],
        x1=25,
        x2=95,
        y1=-TOLERANCIA,
        y2=TOLERANCIA,
        fill="currentColor",
        fillOpacity=0.08,
    ),
    P.ruleY([0], strokeOpacity=0.5),
    puntos("Pisco, ok", lambda r, p: p and estado(r) == "ok"),
    puntos("Pisco, revisar", lambda r, p: p and estado(r) == "revisar"),
    puntos("otro evento", lambda r, p: not p),
    title=f"Pick STA/LTA menos P teórica; la franja marca ±{TOLERANCIA:g} s",
    x={"label": "distancia epicentral (°)", "domain": [25, 95]},
    y={"label": "diferencia (s)", "nice": True},
    grid=True,
)
```

### Dónde falla el detector

```python hidden
por_nombre = {etiqueta(r["traza"]): r for r in resultados}


def ventana(nombre):
    r = por_nombre[nombre]
    p = r["picado"]
    m = (p["t"] > r["teorica"] - 60) & (p["t"] < r["teorica"] + 70)
    marcas = [P.ruleX([r["teorica"]], series="P teórica (iasp91)")]
    if p["pick"] is not None:
        marcas.append(P.ruleX([p["pick"]], series="pick STA/LTA"))
    senal = P.figure(
        P.line(x=p["t"][m], y=p["senal"][m], stroke="currentColor", strokeWidth=0.6),
        *marcas,
        title=f"{nombre}, filtro de 1 a 3 Hz",
        x={"label": "tiempo desde el origen (s)"},
        y={"label": "cuentas"},
        height=220,
        digits=4,
    )
    razon = P.figure(
        P.line(x=p["t"][m], y=p["razon"][m], stroke="currentColor"),
        P.ruleY([UMBRAL], strokeDasharray="4 3"),
        *marcas,
        title=f"{nombre}, STA/LTA ({STA:g} s / {LTA:g} s), umbral {UMBRAL:g}",
        x={"label": "tiempo desde el origen (s)"},
        y={"label": "STA/LTA"},
        height=220,
        digits=4,
    )
    return senal, razon


tuc, kip = ventana("IU.TUC"), ventana("G.KIP")
P.grid(tuc[0], kip[0])
```

```python hidden
P.grid(tuc[1], kip[1])
```

```python hidden
dif = {nombre: r["dif"] for nombre, r in por_nombre.items()}
md(
    f"""
    A la izquierda, un caso que funciona: IU.TUC tiene un ruido muy bajo en 1 a
    3 Hz, la señal lo supera con claridad y el cociente salta muy por encima del
    umbral en pocos segundos. Los picks marcados "revisar" son de tres tipos:

    - **G.KIP, IU.KIP y G.TAOE** ({dif["G.KIP"]:+.1f}, {dif["IU.KIP"]:+.1f} y
      {dif["G.TAOE"]:+.1f} s). El ruido en 1 a 3 Hz es comparable con la señal
      de la onda P y el cociente nunca sube con claridad, como en G.KIP a la
      derecha. El pick es la primera fluctuación que supera el umbral, no la
      llegada. Haría falta otra banda de frecuencia o un umbral por estación.
    - **IU.PMSA** ({dif["IU.PMSA"]:+.1f} s). Un pulso de ruido antes de la P
      cruza el umbral: es una falsa alarma.
    - **IU.POHA** ({dif["IU.POHA"]:+.1f} s). La onda P es emergente: empieza
      con amplitud pequeña que crece despacio, y el cociente cruza el umbral
      después de la llegada real.

    Un detector con parámetros fijos para {len(resultados)} registros de ruido
    y distancia tan distintos no da siempre la misma calidad. Por eso la tabla
    marca qué picks revisar a mano.
    """
)
```

## Espectros de amplitud

Se comparan tres estaciones a distancias distintas. Para cada una se toma una
ventana de señal, de 5 s antes del pick STA/LTA a 115 s después, y una ventana
de ruido, los primeros 40 s del registro, que anteceden a la P. A cada ventana
se le quita la tendencia lineal, se le aplica una ventana de Hann y se calcula
la transformada de Fourier. Para comparar ventanas de longitud distinta, el
espectro se expresa como densidad de amplitud, en cuentas por raíz de hercio.

```python
def densidad_amplitud(x, dt):
    n = np.arange(x.size)
    x = x - np.polyval(np.polyfit(n, x, 1), n)
    w = np.hanning(x.size)
    espectro = np.fft.rfft(x * w)
    f = np.fft.rfftfreq(x.size, dt)
    return f[1:], np.abs(espectro[1:]) * np.sqrt(2 * dt / (x.size * np.mean(w**2)))
```

```python hidden
def espectros(nombre):
    r = por_nombre[nombre]
    tr = r["traza"]
    fs = tr.stats.sampling_rate
    i0 = int((r["picado"]["pick"] - tr.stats.sac.b + tr.stats.sac.o - 5) * fs)
    curvas = {
        "señal (P + 115 s)": tr.data[i0 : i0 + int(120 * fs)].astype(float),
        "ruido (primeros 40 s)": tr.data[: int(40 * fs)].astype(float),
    }
    marcas = []
    for serie, x in curvas.items():
        f, a = densidad_amplitud(x, tr.stats.delta)
        # Unos 200 puntos espaciados en log bastan para el gráfico.
        dentro = np.flatnonzero((f >= 0.01) & (f <= 5))
        idx = np.unique(
            np.geomspace(dentro[0] + 1, dentro[-1] + 1, 200).astype(int) - 1
        )
        marcas.append(P.line(x=f[idx], y=a[idx], series=serie))
    return P.figure(
        *marcas,
        title=f"{nombre}, {tr.stats.sac.gcarc:.1f}°",
        x={"type": "log", "label": "frecuencia (Hz)", "domain": [0.01, 5]},
        y={"type": "log", "label": "cuentas/√Hz"},
        grid=True,
        height=300,
        digits=3,
    )


P.grid(*(espectros(n) for n in ["G.MPG", "IU.TUC", "IU.TSUM"]))
```

En las tres estaciones la densidad de amplitud de la señal es casi plana por
debajo de unos 0.1 Hz y baja más de dos órdenes de magnitud entre 0.1 y 2 Hz,
como corresponde a una fuente que radia sobre todo a periodos largos. La señal
supera al ruido por un factor de decenas a miles bajo 1 Hz. Hacia 3 a 5 Hz las
dos curvas se acercan: el detector STA/LTA de 1 a 3 Hz se apoya en la parte
débil del espectro, y por eso falla en las estaciones ruidosas.

Las alturas absolutas no se comparan entre estaciones: los instrumentos tienen
sensibilidades distintas y el espectro está en cuentas.
