```python hidden
import math

import numba as nb
import numpy as np
from quire import md
from quire import plot as P
```

# Volumen de la hiperesfera en $n$ dimensiones

Objetivo: estimar numéricamente el volumen de la bola
unitaria $$B_n(1)=\{x\in\mathbb{R}^n:\|x\|\le 1\}$$ con Monte Carlo por rechazo
en el cubo $[-1,1]^n$, compararlo con la fórmula exacta y entender por qué el
método falla cuando $n$ crece.

## Resultado analítico

La integral gaussiana en una dimensión
es $$\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}.$$

En $n$
dimensiones, $$\int_{\mathbb{R}^n} e^{-\|x\|^2}\,d^n x = (\sqrt{\pi})^n = \pi^{n/2}.$$

En coordenadas hiperesféricas,

$$ \int_{\mathbb{R}^n} e^{-\|x\|^2}\,d^n x
= S_{n-1}\int_0^{\infty} e^{-r^2}r^{n-1}dr
= S_{n-1}\,\frac{1}{2}\Gamma\!\left(\frac{n}{2}\right),$$
de donde
$$S_{n-1}=\frac{2\pi^{n/2}}{\Gamma(n/2)}.$$

Integrando el área radialmente, el volumen de radio $R$ es
$$V_n(R)=\frac{\pi^{n/2}}{\Gamma\!\left(\frac{n}{2}+1\right)}R^n,
\qquad
V_n(1)=\frac{\pi^{n/2}}{\Gamma\!\left(\frac{n}{2}+1\right)}.$$

## Monte Carlo por rechazo

Se sortean $N$ puntos uniformes en el cubo $[-1,1]^n$, de volumen $2^n$. Si $k$
caen dentro de la bola, la estimación es $\hat V_n = 2^n k/N$. El bucle corta la
suma de $x_i^2$ en cuanto pasa de 1, y numba lo compila.

```python
@nb.njit
def aciertos_acumulados(dim, puntos_control, semilla):
    """Aciertos dentro de la bola al llegar a cada tamaño de `puntos_control`.

    Una sola corrida de muestras; `puntos_control` es creciente.
    """
    np.random.seed(semilla)
    salida = np.empty(puntos_control.shape[0], dtype=np.int64)
    aciertos = 0
    hechos = 0
    for c in range(puntos_control.shape[0]):
        for _ in range(puntos_control[c] - hechos):
            r2 = 0.0
            for _d in range(dim):
                x = np.random.uniform(-1.0, 1.0)
                r2 += x * x
                if r2 > 1.0:
                    break
            if r2 <= 1.0:
                aciertos += 1
        hechos = puntos_control[c]
        salida[c] = aciertos
    return salida


def volumen_exacto(dim):
    return math.pi ** (dim / 2.0) / math.gamma(dim / 2.0 + 1.0)


def tasa_exacta(dim):
    """Fracción del cubo [-1, 1]^dim que ocupa la bola: V_n / 2^n."""
    return volumen_exacto(dim) / 2.0**dim


N_MUESTRAS = 1_000_000
DIMENSIONES = np.arange(1, 21)
SEMILLA = 12345

aciertos = np.array(
    [
        aciertos_acumulados(int(n), np.array([N_MUESTRAS]), SEMILLA + int(n))[0]
        for n in DIMENSIONES
    ]
)
exacto = np.array([volumen_exacto(int(n)) for n in DIMENSIONES])
tasa = np.array([tasa_exacta(int(n)) for n in DIMENSIONES])
tasa_mc = aciertos / N_MUESTRAS
estimado = tasa_mc * 2.0**DIMENSIONES
# Desviación típica de 2^n k / N, con k binomial(N, p).
sigma = 2.0**DIMENSIONES * np.sqrt(tasa * (1.0 - tasa) / N_MUESTRAS)
error_relativo = np.abs(estimado - exacto) / exacto
error_esperado = sigma / exacto
n_pico = int(DIMENSIONES[np.argmax(exacto)])
```

```python hidden
n_fino = np.linspace(1.0, 10.0, 90001)
v_fino = np.exp(
    n_fino / 2.0 * math.log(math.pi)
    - np.array([math.lgamma(x / 2 + 1) for x in n_fino])
)
n_pico_continuo = float(n_fino[np.argmax(v_fino)])

filas_volumen = [
    f"| {n} | {ex:.6f} | {est:.6f} | {int(h):,} | {p:.3e} |"
    for n, ex, est, h, p in zip(
        DIMENSIONES, exacto, estimado, aciertos, tasa, strict=True
    )
    if n in (2, 3, 4, 5, 6, 8, 10, 12, 15, 20)
]
md(
    "\n".join(
        [
            f"$N={N_MUESTRAS:,}$ puntos por dimensión.",
            "",
            r"| $n$ | $V_n$ exacto | $\hat V_n$ | aciertos $k$ | $V_n/2^n$ |",
            "|---:|---:|---:|---:|---:|",
            *filas_volumen,
        ]
    )
)
```

```python hidden
md(
    rf"""
    El volumen exacto es máximo en $n={n_pico}$, con
    $V_{{{n_pico}}}=8\pi^2/15\approx{exacto[n_pico - 1]:.4f}$. Si $n$ se toma
    como variable continua, el máximo está en $n\approx{n_pico_continuo:.2f}$.
    Para $n>5$ la bola unitaria pierde volumen y $V_n\to 0$. Las barras marcan
    $\pm2\sigma$: con $N$ fijo se vuelven visibles desde $n\approx10$, porque
    $\sigma/V_n$ crece con $n$.
    """
)
```

```python hidden
P.figure(
    P.line(x=DIMENSIONES, y=exacto, series="exacto"),
    P.ruleX(
        x=DIMENSIONES,
        y1=estimado - 2 * sigma,
        y2=estimado + 2 * sigma,
        series=f"Monte Carlo, N = {N_MUESTRAS:,}",
    ),
    P.dot(x=DIMENSIONES, y=estimado, r=3.5, series=f"Monte Carlo, N = {N_MUESTRAS:,}"),
    P.ruleX([n_pico], strokeDasharray="4 3", strokeOpacity=0.6),
    P.text(
        x=[n_pico],
        y=[exacto[n_pico - 1]],
        text=[f"máximo en n = {n_pico}"],
        textAnchor="start",
        dx=8,
        dy=-10,
    ),
    title="Volumen de la bola unitaria",
    x={"label": "dimensión n", "ticks": DIMENSIONES[1::2]},
    y={"label": "Vₙ"},
    grid=True,
)
```

## Por qué falla en dimensión alta

La tasa de aceptación es la fracción del cubo que ocupa la bola, $p_n=V_n/2^n$.
Con la aproximación de Stirling para $\Gamma(n/2+1)$,
$$p_n \approx \frac{1}{\sqrt{\pi n}}\left(\frac{\pi e}{2n}\right)^{n/2},$$
que cae más rápido que cualquier exponencial: el factor entre paréntesis ya es
menor que 1 para $n\ge 5$.

Un punto uniforme del cubo cumple $\|x\|^2=\sum_i x_i^2\approx n/3$, que supera
1 para $n>3$. La norma se concentra alrededor de $\sqrt{n/3}$ con un ancho que
no crece con $n$: casi todo el volumen del cubo está en sus esquinas, fuera de
la bola. La animación recorre $n$ con la distribución de $\|x\|$ para 100 000
puntos del cubo; la parte a la izquierda de $\|x\|=1$ es la que acierta.

```python hidden
BORDES = np.arange(0.0, 4.55, 0.05)
rng_normas = np.random.default_rng(5)
densidades = []
dentro_medido = []
for n in DIMENSIONES:
    normas = np.sqrt(np.sum(rng_normas.uniform(-1, 1, size=(100_000, n)) ** 2, axis=1))
    densidades.append(np.histogram(normas, bins=BORDES, density=True)[0])
    dentro_medido.append(np.mean(normas <= 1.0))
densidades = np.array(densidades)
izquierda = BORDES[:-1] < 1.0 - 1e-9


def barras(cuales, nombre):
    return P.rectY(
        x1=BORDES[:-1][cuales],
        x2=BORDES[1:][cuales],
        y=densidades[:, cuales],
        series=nombre,
        inset=0,
        tip=False,
    )


P.figure(
    barras(izquierda, "dentro de la bola"),
    barras(~izquierda, "fuera"),
    P.ruleX(x=np.sqrt(DIMENSIONES / 3)[:, None], strokeDasharray="4 3"),
    P.text(
        x=[0.05],
        y=[1.85],
        text=np.array(
            [
                [f"n = {n}: dentro {d:.2%}\n√(n/3) = {np.sqrt(n / 3):.2f} (guiones)"]
                for n, d in zip(DIMENSIONES, dentro_medido, strict=True)
            ]
        ),
        textAnchor="start",
        lineAnchor="top",
    ),
    title="Distribución de ‖x‖ para puntos uniformes del cubo",
    frames=[f"n = {n}" for n in DIMENSIONES],
    fps=2,
    x={"domain": [0, 4.5], "label": "norma ‖x‖"},
    y={"domain": [0, 1.9], "label": "densidad"},
    digits=3,
)
```

La tasa medida $k/N$ sigue a $p_n$ hasta que cae por debajo de $1/N$: ahí la
corrida espera menos de un acierto. Sin aciertos, $\hat V_n=0$ y el error
relativo es 1. El panel derecho omite $n=1$, donde la bola llena el segmento y
no hay error.

```python hidden
visibles = tasa_mc > 0
P.grid(
    P.figure(
        P.line(x=DIMENSIONES, y=tasa, series="pₙ exacta"),
        P.dot(x=DIMENSIONES[visibles], y=tasa_mc[visibles], r=3.5, series="k/N medida"),
        P.ruleY([1 / N_MUESTRAS], strokeDasharray="4 3", strokeOpacity=0.6),
        P.text(
            x=[1.5],
            y=[1 / N_MUESTRAS],
            text=["1/N"],
            textAnchor="start",
            dy=-8,
        ),
        title="Aceptación del rechazo en el cubo",
        x={"label": "dimensión n", "ticks": DIMENSIONES[1::2]},
        y={
            "type": "log",
            "label": "tasa de aceptación",
            "domain": [1e-9, 1],
            "ticks": [1e-9, 1e-6, 1e-3, 1],
        },
        grid=True,
    ),
    P.figure(
        P.line(x=DIMENSIONES[1:], y=error_esperado[1:], series="esperado σ/Vₙ"),
        P.dot(x=DIMENSIONES[1:], y=error_relativo[1:], r=3.5, series="medido"),
        title=f"Error relativo con N = {N_MUESTRAS:,}",
        x={"label": "dimensión n", "ticks": DIMENSIONES[1::2]},
        y={
            "type": "log",
            "label": "error relativo",
            "domain": [1e-6, 10],
            "ticks": [1e-6, 1e-4, 1e-2, 1],
        },
        grid=True,
    ),
)
```

```python hidden
sin_aciertos = ", ".join(str(int(n)) for n in DIMENSIONES[aciertos == 0])
filas_costo = [
    f"| {n} | {p:.3e} | {(1 - p) / (p * 0.01**2):.3e} |"
    for n, p in zip(DIMENSIONES, tasa, strict=True)
    if n in (2, 5, 10, 15, 20)
]
md(
    "\n".join(
        [
            r"El estimador $\hat V_n=2^nk/N$ tiene error relativo típico",
            r"$\sqrt{(1-p_n)/(p_nN)}$. Para fijar ese error en 1 % hacen falta",
            r"$N\approx(1-p_n)/(p_n\,10^{-4})$ puntos:",
            "",
            "| $n$ | $p_n$ | $N$ para error del 1 % |",
            "|---:|---:|---:|",
            *filas_costo,
            "",
            f"Con $N={N_MUESTRAS:,}$ la corrida no tiene ningún acierto para",
            f"$n={sin_aciertos}$. Aumentar $N$ no arregla el método, porque el",
            r"costo crece como $1/p_n$, es decir, más rápido que una exponencial en",
            "$n$.",
        ]
    )
)
```

Esto es una muestra de la *maldición de la dimensionalidad*. Hinrichs, Prochno y
Ullrich (J. Complexity 50, 2019) demuestran que, para integrar funciones suaves
sobre dominios como el cubo o las bolas $\ell_p$, el número de evaluaciones que
necesita un algoritmo lineal determinista en el peor caso crece
exponencialmente con la dimensión. Su técnica usa que el volumen de un cuerpo
convexo isótropo se concentra en una capa delgada alrededor de su radio típico.
Ese resultado no trata el rechazo en el cubo; es el marco general en el que este
fallo encaja.

## Convergencia con $N$

Una sola corrida por dimensión registra los aciertos acumulados en 17 tamaños
entre $10^2$ y $10^6$. El error relativo esperado es
$\sqrt{(1-p_n)/(p_nN)}$.

```python
CONTROL = np.unique(np.logspace(2, 6, 17).astype(np.int64))
DIMS_CONVERGENCIA = (2, 4, 8, 12)
convergencia = {}
for n in DIMS_CONVERGENCIA:
    k = aciertos_acumulados(n, CONTROL, 99 + n)
    estimacion = 2.0**n * k / CONTROL
    convergencia[n] = np.abs(estimacion - volumen_exacto(n)) / volumen_exacto(n)
```

```python hidden
marcas_convergencia = []
for n in DIMS_CONVERGENCIA:
    p = tasa_exacta(n)
    marcas_convergencia += [
        P.line(
            x=CONTROL,
            y=convergencia[n],
            marker="dot",
            series=f"n = {n}",
        ),
        P.line(
            x=CONTROL,
            y=np.sqrt((1 - p) / (p * CONTROL)),
            strokeDasharray="5 3",
            series=f"n = {n}",
            tip=False,
        ),
    ]

P.figure(
    *marcas_convergencia,
    title="Error relativo: medido (puntos) y esperado (guiones)",
    x={"type": "log", "label": "número de muestras N"},
    y={
        "type": "log",
        "label": "error relativo",
        "domain": [1e-5, 10],
        "ticks": [1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1, 10],
    },
    grid=True,
)
```

En cada dimensión el error decae como $N^{-1/2}$, pero la constante
$\sqrt{(1-p_n)/p_n}$ crece con $n$. La curva medida sigue a la esperada con las
fluctuaciones propias de una sola corrida.
$$
