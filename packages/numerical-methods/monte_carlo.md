```python hidden
import numpy as np
from quire import md, parameter
from quire import plot as P
```

# Integración de Monte Carlo

En física estadística, un observable es un valor esperado sobre un espacio de
configuraciones $R$ de dimensión alta, $\langle A\rangle = Z^{-1}\int e^{-\beta
H(R)}A(R)\,dR$. Una malla regular de $n$ nodos por dirección necesita $N=n^d$
puntos, y una regla de orden $k$ tiene error $\sim N^{-k/d}$: se degrada con la
dimensión $d$. Monte Carlo tiene error $\sim N^{-1/2}$ en cualquier $d$.

Sea $\Omega$ una región de volumen $V_\Omega$ y $X_1,\ldots,X_N$ puntos
independientes y uniformes en $\Omega$. Entonces

$$
\begin{aligned}
I &= \int_\Omega f(x)\,dx \approx \hat I_N,\\
\hat I_N &= V_\Omega\,\note{la media muestral de
$f$}{\frac1N\sum_{i=1}^N f(X_i)},\\
\sigma_{\hat I} &= V_\Omega\,\note{no depende de la dimensión de
$\Omega$}{\frac{1}{\sqrt N}}\sqrt{\operatorname{Var}f(X)},
\end{aligned}
$$

y $\operatorname{Var}f(X)$ se estima con la varianza muestral $s_f^2$ (`ddof=1`
en NumPy). El error estándar $V_\Omega s_f/\sqrt N$ es el error típico de $\hat
I_N$.

## Tres integrales con valor conocido

1. $\pi=\displaystyle\iint_{[-1,1]^2}\mathbf 1_{x^2+y^2\le1}\,dx\,dy$, con
   $V_\Omega=4$.
2. $\pi=\displaystyle\int_0^2\sqrt{4-x^2}\,dx$ (un cuarto de círculo de radio
   2), con $V_\Omega=2$.
3. $1=\displaystyle\int_0^1\!\!\int_0^1 9x^2y^2\,dx\,dy$, con $V_\Omega=1$.

```python
def muestra_pi(rng, n):
    puntos = rng.uniform(-1.0, 1.0, size=(n, 2))
    return 4.0, (np.sum(puntos**2, axis=1) <= 1.0).astype(float)


def muestra_1d(rng, n):
    x = rng.uniform(0.0, 2.0, size=n)
    return 2.0, np.sqrt(4.0 - x**2)


def muestra_2d(rng, n):
    x, y = rng.uniform(0.0, 1.0, size=(2, n))
    return 1.0, 9.0 * x**2 * y**2


problemas = {
    "π (indicadora)": (muestra_pi, np.pi),
    "π (1D)": (muestra_1d, np.pi),
    "integral 2D": (muestra_2d, 1.0),
}


def estimador(muestra, rng, n):
    """Devuelve la estimación de la integral y su error estándar."""
    volumen, valores = muestra(rng, n)
    return volumen * valores.mean(), volumen * valores.std(ddof=1) / np.sqrt(n)
```

```python
N_TABLA = 10_000
rng_tabla = np.random.default_rng(42)
filas = []
for nombre, (muestra, exacto) in problemas.items():
    estimacion, se = estimador(muestra, rng_tabla, N_TABLA)
    filas.append(
        f"| {nombre} | {estimacion:.5f} | {exacto:.5f} "
        f"| {abs(estimacion - exacto):.5f} | {se:.5f} |"
    )
md(
    "\n".join(
        [
            f"$N={N_TABLA}$, semilla 42.",
            "",
            "| integral | estimación | exacto | error | error estándar |",
            "|---|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

La figura sigue la primera integral con los primeros $N$ puntos de una corrida,
uniformes en el cuadrado, de un color si caen en el círculo y de otro si no. A
la derecha, $\hat I_N = 4\cdot(\text{fracción dentro})$ oscila al crecer $N$ y
se acerca a $\pi$ dentro de la banda $\pi\pm2\sigma_{\hat I}$, que se estrecha
como $N^{-1/2}$.

```python hidden
N_MAX = 5000
rng_animacion = np.random.default_rng(3)
puntos = rng_animacion.uniform(-1.0, 1.0, size=(N_MAX, 2))
dentro = np.sum(puntos**2, axis=1) <= 1.0
estimacion_pi = 4.0 * np.cumsum(dentro) / np.arange(1, N_MAX + 1)
cortes = np.unique(np.round(np.geomspace(10, N_MAX, 90)).astype(int))
marcas = np.unique(np.round(np.geomspace(10, N_MAX, 400)).astype(int))
p_dentro = np.pi / 4
sigma_pi = 4.0 * np.sqrt(p_dentro * (1 - p_dentro) / marcas)

# El punto j aparece en el primer cuadro cuyo corte lo incluye.
cuadro_punto = np.searchsorted(cortes, np.arange(N_MAX), side="right")
cuadro_marca = np.searchsorted(cortes, marcas)
angulo = np.linspace(0, 2 * np.pi, 200)

muestras = parameter("N", cortes, value=cortes[len(cortes) // 2])
estimacion_cortes = estimacion_pi[cortes - 1]
sigma_cortes = 4.0 * np.sqrt(p_dentro * (1 - p_dentro) / cortes)
md(
    rf"""
    Arrastra $N$: con $N = {muestras}$ puntos la estimación es
    {muestras.each(estimacion_cortes):.4f}, a
    {muestras.each(np.abs(estimacion_cortes - np.pi) / sigma_cortes):.1f}
    $\sigma_{{\hat I}}$ de $\pi$.
    """
)
```

```python hidden
def nube(cuales, nombre):
    return P.dot(
        x=puntos[cuales, 0],
        y=puntos[cuales, 1],
        since=cuadro_punto[cuales],
        r=1.5,
        series=nombre,
        tip=False,
    )


P.grid(
    P.figure(
        nube(dentro, "dentro del círculo"),
        nube(~dentro, "fuera"),
        P.line(x=np.cos(angulo), y=np.sin(angulo), stroke="currentColor"),
        title="Puntos al azar en el cuadrado",
        frames=muestras,
        x={"domain": [-1.05, 1.05], "label": None, "ticks": 5},
        y={"domain": [-1.05, 1.05], "label": None, "ticks": 5},
        aspectRatio=1,
        digits=3,
    ),
    P.figure(
        P.areaY(
            x=marcas,
            y1=np.pi - 2 * sigma_pi,
            y2=np.pi + 2 * sigma_pi,
            fillOpacity=0.25,
            clip=True,
            series="π ± 2σ",
        ),
        P.ruleY([np.pi], strokeDasharray="4 3", strokeOpacity=0.6),
        P.line(
            x=marcas,
            y=estimacion_pi[marcas - 1],
            since=cuadro_marca,
            series="estimación",
        ),
        P.dot(
            x=cortes[:, None],
            y=estimacion_cortes[:, None],
            r=4,
            series="estimación",
        ),
        title="4 · fracción dentro",
        frames=muestras,
        x={"type": "log", "domain": [10, 1.25 * N_MAX], "label": "N"},
        y={"domain": [2.2, 4.1], "label": "estimación"},
        grid=True,
    ),
)
```

El error absoluto de una corrida es del tamaño del error estándar, pero fluctúa
de una corrida a otra.

## Convergencia: error $\sim N^{-1/2}$

Para ver la ley de potencias hay que promediar esa fluctuación. Repetimos cada
estimación 200 veces con muestras nuevas, para $N$ entre $10^2$ y $10^5$, y
graficamos la raíz del error cuadrático medio (RMS) contra $N$. El ajuste de
$\log(\mathrm{RMS})$ contra $\log N$ da la pendiente.

```python
TAMANOS = np.unique(np.logspace(2, 5, 7).astype(int))
REPETICIONES = 200

rng_convergencia = np.random.default_rng(2024)
rms = {}
error_estandar = {}
for nombre, (muestra, exacto) in problemas.items():
    errores_rms, errores_se = [], []
    for n in TAMANOS:
        corridas = np.array(
            [estimador(muestra, rng_convergencia, int(n)) for _ in range(REPETICIONES)]
        )
        errores_rms.append(np.sqrt(np.mean((corridas[:, 0] - exacto) ** 2)))
        errores_se.append(corridas[:, 1].mean())
    rms[nombre] = np.array(errores_rms)
    error_estandar[nombre] = np.array(errores_se)

pendientes = {
    nombre: np.polyfit(np.log(TAMANOS), np.log(valores), 1)[0]
    for nombre, valores in rms.items()
}
```

```python hidden
PANELES = [f"{nombre}: pendiente {pendientes[nombre]:.3f}" for nombre in rms]


def por_panel(series):
    """Une una serie por problema en un canal, con su panel en fx."""
    return {
        "x": np.tile(TAMANOS, len(PANELES)),
        "y": np.concatenate(series),
        "fx": np.repeat(PANELES, len(TAMANOS)),
    }


P.figure(
    P.line(
        **por_panel([rms[n] for n in rms]),
        marker="dot",
        series=f"RMS de {REPETICIONES} corridas",
    ),
    P.line(
        **por_panel([error_estandar[n] for n in rms]),
        strokeDasharray="5 3",
        series="error estándar",
    ),
    P.line(
        **por_panel([rms[n][0] * (TAMANOS[0] / TAMANOS) ** 0.5 for n in rms]),
        strokeDasharray="1 3",
        series="N⁻¹ᐟ²",
    ),
    x={"type": "log", "label": "N"},
    title=f"Error contra N, {REPETICIONES} corridas por punto",
    y={
        "type": "log",
        "label": "error",
        "domain": [1e-3, 0.2],
        "ticks": [1e-3, 1e-2, 1e-1],
    },
    fx={"domain": PANELES, "label": None},
    grid=True,
)
```

```python hidden
md(
    f"""
    Las pendientes ajustadas ({", ".join(f"{p:.2f}" for p in pendientes.values())})
    son cercanas a $-1/2$ en los tres problemas: el exponente no depende de la
    dimensión (2, 1 y 2 variables) ni del integrando. El error estándar calculado
    desde una sola muestra coincide con el RMS medido, así que se puede reportar
    sin repetir la simulación.
    """
)
```

## Reducción de varianza: muestreo por importancia

Con $N^{-1/2}$ no se puede mejorar la pendiente, pero sí el factor
$\sqrt{\operatorname{Var}}$. Si se muestrea con una densidad $p(x)$ en lugar de
la uniforme,

$$
\begin{aligned}
I &= \int f(x)\,dx=\int \frac{f(x)}{p(x)}\,p(x)\,dx\\
&= \mathbb E_p\!\left[\frac{f(X)}{p(X)}\right],\\
\hat I_N &= \frac1N\sum_{i=1}^N\frac{f(X_i)}{p(X_i)},\ \ X_i\sim p.
\end{aligned}
$$

La varianza se anula si $p\propto f$, y crece si $p$ se aparta de $f$ o es menor
que $f$ donde $f$ es grande. En el caso $f=9x^2y^2$ sobre el cuadrado unitario
usamos la familia $p_a(x,y)=(a+1)^2x^ay^a$, que se muestrea con la inversa de la
distribución acumulada, $x=u^{1/(a+1)}$. El caso $a=0$ es el muestreo uniforme.
El peso es $w=f/p_a=\dfrac{9}{(a+1)^2}(xy)^{2-a}$, y

$$
\operatorname{Var}_{p_a}(w)=\frac{81}{(a+1)^2(5-a)^2}-1.
$$

Esa varianza es 2.24 para $a=0$ y se anula en $a=2$, donde $p_a\propto f$ y el
peso es constante.

```python
def importancia(rng, n, a):
    """Estimación de la integral 2D con muestras de p_a y su error estándar."""
    x, y = rng.uniform(size=(2, n)) ** (1.0 / (a + 1.0))
    pesos = 9.0 / (a + 1.0) ** 2 * (x * y) ** (2.0 - a)
    return pesos.mean(), pesos.std(ddof=1) / np.sqrt(n)


def varianza_teorica(a):
    return 81.0 / ((a + 1.0) ** 2 * (5.0 - a) ** 2) - 1.0


N_IMPORTANCIA = 10_000
EXPONENTES = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])

rng_importancia = np.random.default_rng(7)
sigma_medida = np.array(
    [
        np.std(
            [importancia(rng_importancia, N_IMPORTANCIA, a)[0] for _ in range(200)],
            ddof=1,
        )
        for a in EXPONENTES
    ]
)
```

```python hidden
a_fino = np.linspace(0.0, 4.0, 200)
medidas = sigma_medida > 0

P.figure(
    P.line(
        x=a_fino,
        y=np.sqrt(np.maximum(varianza_teorica(a_fino), 1e-12) / N_IMPORTANCIA),
        series="teoría",
    ),
    P.dot(
        x=EXPONENTES[medidas],
        y=sigma_medida[medidas],
        r=4,
        series="desviación de 200 corridas",
    ),
    title="Muestreo por importancia, f = 9x²y²",
    x={"label": "exponente a de pₐ"},
    y={"type": "log", "label": f"desviación del estimador, N = {N_IMPORTANCIA}"},
    grid=True,
)
```

```python hidden
indice = {float(a): i for i, a in enumerate(EXPONENTES)}
uniforme = sigma_medida[indice[0.0]]
lineal = sigma_medida[indice[1.0]]
md(
    rf"""
    Con muestreo uniforme ($a=0$) la desviación del estimador es {uniforme:.4f}.
    Con $a=1$ (densidad lineal en cada coordenada) baja a {lineal:.4f}, es decir,
    {(uniforme / lineal) ** 2:.1f} veces menos varianza con el mismo $N$. Con $a=2$
    el peso es constante y la desviación es cero salvo error de redondeo. Más allá
    de $a=2$ la varianza vuelve a subir, porque $p_a$ cae más rápido que $f$ cerca
    de $x=0$. Este caso se eligió porque se conoce $p\propto f$; en un problema real
    $f$ no se conoce de antemano, y el esfuerzo se va en encontrar una $p$ que lo
    aproxime y se pueda muestrear. Esa es la idea detrás de Metropolis cuando $p$
    es el factor de Boltzmann.
    """
)
```
