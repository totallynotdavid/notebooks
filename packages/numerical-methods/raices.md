```python hidden
from decimal import Decimal, getcontext

import numpy as np
from quire import md
from quire import plot as P
```

# Solución de ecuaciones no lineales

Se busca $x^\ast$ con $f(x^\ast)=0$. Tres métodos, con lo que exigen y lo que
dan:

| método         | necesita                | convergencia                  |
| -------------- | ----------------------- | ----------------------------- |
| bisección      | $f(a)f(b)<0$            | lineal, razón $\tfrac12$      |
| falsa posición | $f(a)f(b)<0$            | lineal, razón depende de $f$  |
| Newton         | $f'$ y un punto inicial | cuadrática en una raíz simple |

Cada iteración:

- **Bisección:** $c=\frac{a+b}{2}$; se queda con el lado donde $f$ cambia de
  signo.
- **Falsa posición:** $c=\dfrac{af(b)-bf(a)}{f(b)-f(a)}$, el corte de la cuerda
  con el eje, con el mismo criterio de signo.
- **Newton:** $x_{k+1}=x_k-\dfrac{f(x_k)}{f'(x_k)}$.

La convergencia de orden $p$ significa $e_{k+1}\approx C\,e_k^{\,p}$, con
$e_k=|x_k-x^\ast|$. En una gráfica semilogarítmica de $e_k$ contra $k$, un
método lineal es una recta y uno cuadrático cae cada vez más rápido: el número
de cifras correctas se duplica en cada paso.

```python
def biseccion(f, a, b, n):
    """n pasos de bisección. Devuelve los puntos medios y las semianchuras.

    Después de cada paso se toma el punto medio del intervalo que queda. Su
    semianchura acota el error, que en la práctica puede ser mucho menor.
    """
    fa = f(a)
    if fa * f(b) > 0:
        raise ValueError("f(a) y f(b) deben tener signos opuestos")
    medios, anchos = [], []
    for _ in range(n):
        c = (a + b) / 2
        fc = f(c)
        if fc == 0:
            medios.append(c)
            anchos.append(0.0)
            break
        if np.sign(fc) == np.sign(fa):
            a, fa = c, fc
        else:
            b = c
        medios.append((a + b) / 2)
        anchos.append((b - a) / 2)
    return np.array(medios), np.array(anchos)


def falsa_posicion(f, a, b, n):
    """n pasos de falsa posición. Devuelve las abscisas del corte y el
    intervalo [a, b] cuya cuerda dio cada una."""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError("f(a) y f(b) deben tener signos opuestos")
    cortes, intervalos = [], []
    for _ in range(n):
        c = (a * fb - b * fa) / (fb - fa)
        fc = f(c)
        cortes.append(c)
        intervalos.append((a, b))
        if fc == 0:
            break
        if np.sign(fc) == np.sign(fa):
            a, fa = c, fc
        else:
            b, fb = c, fc
    return np.array(cortes), np.array(intervalos)


def newton(f, df, x0, n, multiplicidad=1):
    """n pasos de Newton. `multiplicidad` = 1 es el método clásico."""
    x = x0
    iterados = []
    for _ in range(n):
        derivada = df(x)
        if derivada == 0:
            break
        x = x - multiplicidad * f(x) / derivada
        iterados.append(x)
    return np.array(iterados)
```

## Bisección con $f(x)=x^3+1$

Con el intervalo $[-3,2]$, $f(-3)=-26<0<f(2)=9$ y la raíz es $-1$. En cada paso
el intervalo se reduce a la mitad, así que tras $n$ pasos el punto medio del
intervalo que queda está a menos de $(b-a)/2^{n+1}$ de la raíz. Para llegar a
una tolerancia $\tau$ hacen falta $n\ge\log_2\frac{b-a}{\tau}-1$ pasos, sin
importar $f$.

```python
def cubo_mas_uno(x):
    return x**3 + 1


filas = []
for tol in (1e-2, 1e-4, 1e-6, 1e-8):
    n = int(np.ceil(np.log2(5 / tol) - 1))
    medios, anchos = biseccion(cubo_mas_uno, -3.0, 2.0, n)
    filas.append(
        f"| {tol:.0e} | {n} | {medios[-1]:.9f} | {abs(medios[-1] + 1):.1e} "
        f"| {anchos[-1]:.1e} |"
    )
md(
    "\n".join(
        [
            "| $\\tau$ | pasos $n$ | $x_n$ | error real | semianchura |",
            "|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

El error real queda por debajo de la semianchura, que es la cota garantizada, y
por eso $n$ no depende de dónde esté la raíz dentro del intervalo.

## Los tres métodos en $f(x)=x^3+5x^2+2$

$f'(x)=3x^2+10x$. Esta función tiene una sola raíz real, $x^\ast\approx-5.0776$
(las otras dos son complejas), y está en $[-6,-4]$, donde
$f(-6)=-34<0<f(-4)=18$. Para medir el error con más cifras que `float64` se
calcula la raíz con 60 dígitos (`decimal`) y se compara cada iterado, convertido
exactamente, contra ella.

```python
getcontext().prec = 60


def f_cubica(x):
    return x**3 + 5 * x**2 + 2


def df_cubica(x):
    return 3 * x**2 + 10 * x


def raiz_alta_precision(x0):
    x = Decimal(x0)
    for _ in range(100):
        x -= (x**3 + 5 * x**2 + 2) / (3 * x**2 + 10 * x)
    return x


RAIZ = raiz_alta_precision(-5)


def error_absoluto(iterados):
    """|x_k - x*| calculado con 60 dígitos."""
    return [abs(Decimal(float(x)) - RAIZ) for x in iterados]


medios, anchos_biseccion = biseccion(f_cubica, -6.0, -4.0, 50)
cortes, intervalos_falsa = falsa_posicion(f_cubica, -6.0, -4.0, 40)
historias = {
    "bisección": medios,
    "falsa posición": cortes,
    "Newton ($x_0=-6$)": newton(f_cubica, df_cubica, -6.0, 6),
}
errores = {
    nombre: np.array([float(e) for e in error_absoluto(h)])
    for nombre, h in historias.items()
}
```

Las animaciones siguen a cada método hasta muy cerca de la raíz. Cada paso
aparece primero en la ventana del paso anterior, y luego la ventana se acerca al
nuevo $x_k$. Los pasos anteriores quedan tenues. La esquina da $x_k$, su error y
el ancho de la ventana.

```python hidden
CUADROS_PASO, CUADROS_ZOOM = 5, 9
INICIO = CUADROS_PASO + CUADROS_ZOOM
RAIZ_F = float(RAIZ)
# Puntos cada vez más juntos cerca de la raíz, para que la curva siga suave
# cuando la ventana mide 10⁻⁸.
_lejos = np.logspace(0.4, -10, 400)
CURVA_X = RAIZ_F + np.concatenate([-_lejos, _lejos[::-1]])
HALO = {"stroke": "var(--plot-background)", "strokeWidth": 6, "fill": "currentColor"}
CONTORNO = {"stroke": "var(--plot-background)", "strokeWidth": 1.5}


def recorrido(centros, semianchos):
    """Paso que muestra cada cuadro y el dominio [min, max] de x en ese cuadro.

    El paso j se ve primero en la ventana del paso j−1. Luego el semiancho se
    reduce geométricamente hasta el del paso j, y el centro lo sigue.
    """
    c = np.concatenate([[-5.0], centros])
    w = np.concatenate([[1.2], semianchos])
    suave = (1 - np.cos(np.pi * np.arange(1, CUADROS_ZOOM + 1) / CUADROS_ZOOM)) / 2
    t = np.concatenate([np.zeros(CUADROS_PASO), suave])
    pasos, dominios = [], []
    for j in range(len(centros)):
        ancho = w[j] * (w[j + 1] / w[j]) ** t
        avance = (w[j] - ancho) / (w[j] - w[j + 1])
        centro = c[j] + (c[j + 1] - c[j]) * avance
        pasos.append(np.full(len(t), j))
        dominios.append(np.column_stack([centro - ancho, centro + ancho]))
    return np.concatenate(pasos), np.concatenate(dominios)


def eje_y(dominios):
    """El rango de f en cada ventana de x, con margen."""
    muestra = f_cubica(np.linspace(dominios[:, 0], dominios[:, 1], 65))
    bajo, alto = muestra.min(axis=0), muestra.max(axis=0)
    margen = 0.15 * (alto - bajo)
    return np.column_stack([bajo - margen, alto + margen])


def animacion(marcas, pasos, dominios, iterados, error, titulo):
    """Curva, eje, marcas del método y la leyenda de cada cuadro."""
    leyenda = [
        f"k = {j + 1}\nxₖ = {iterados[j]:.12f}\neₖ = {error[j]:.1e}\n"
        f"ventana: {hi - lo:.1e}"
        for j, (lo, hi) in zip(pasos, dominios, strict=True)
    ]
    return P.figure(
        P.line(
            x=CURVA_X,
            y=f_cubica(CURVA_X),
            stroke="currentColor",
            strokeOpacity=0.45,
            clip=True,
        ),
        P.ruleY([0], strokeOpacity=0.6),
        *marcas,
        P.text(
            text=np.array(leyenda)[:, None],
            # f crece a través de la raíz: la esquina inferior derecha queda libre.
            frameAnchor="bottom-right",
            lineAnchor="bottom",
            textAnchor="end",
            lineHeight=1.3,
            dx=-8,
            dy=-8,
            **HALO,
        ),
        title=titulo,
        frames=[f"k = {j + 1}" for j in pasos],
        fps=12,
        digits=12,
        x={"domain": dominios, "label": "x", "ticks": 3},
        y={"domain": eje_y(dominios), "label": "f(x)", "ticks": 4},
        grid=True,
    )
```

**Bisección.** La barra es el intervalo que queda y el punto, su punto medio.
Cada paso parte el intervalo en dos.

```python hidden
N_BIS = 18
m, h = medios[:N_BIS], anchos_biseccion[:N_BIS]
pasos, dominios = recorrido(m, 1.5 * h)
inicio = np.arange(N_BIS) * INICIO
padre_m = np.concatenate([[-5.0], m])[pasos, None]
padre_h = np.concatenate([[1.0], h])[pasos, None]
COLOR = "var(--chart-1)"
animacion(
    [
        P.link(
            x1=padre_m - padre_h,
            x2=padre_m + padre_h,
            y1=[0.0],
            y2=[0.0],
            stroke=COLOR,
            strokeWidth=10,
            strokeOpacity=0.2,
            clip=True,
        ),
        P.dot(
            x=m,
            y=np.zeros(N_BIS),
            since=inicio,
            r=2,
            fill="currentColor",
            fillOpacity=0.5,
            clip=True,
        ),
        P.link(
            x1=(m - h)[pasos, None],
            x2=(m + h)[pasos, None],
            y1=[0.0],
            y2=[0.0],
            stroke=COLOR,
            strokeWidth=10,
            strokeOpacity=0.5,
            clip=True,
        ),
        P.link(
            x1=m[pasos, None],
            x2=m[pasos, None],
            y1=[0.0],
            y2=f_cubica(m)[pasos, None],
            stroke=COLOR,
            strokeDasharray="2 3",
            clip=True,
        ),
        P.dot(x=m[pasos, None], y=[0.0], r=4.5, fill=COLOR, clip=True, **CONTORNO),
    ],
    pasos,
    dominios,
    m,
    errores["bisección"],
    "Bisección, f(x) = x³ + 5x² + 2",
)
```

```python hidden
razon_falsa = errores["falsa posición"][11] / errores["falsa posición"][10]
md(
    rf"""**Falsa posición.** La cuerda une $(a,f(a))$ y $(b,f(b))$, y su corte con
el eje es el nuevo $x_k$. En $[-6,-4]$ la función es cóncava ($f''=6x+10<0$),
así que el extremo izquierdo, $-6$, nunca cambia y el error se reduce por un factor casi
fijo, {razon_falsa:.2f} en el paso 12."""
)
```

```python hidden
N_FALSA = 12
x_f = cortes[:N_FALSA]
a, b = intervalos_falsa[:N_FALSA].T
e_f = errores["falsa posición"]
pasos, dominios = recorrido(x_f, 4 * e_f[:N_FALSA])
inicio = np.arange(N_FALSA) * INICIO
COLOR = "var(--chart-2)"
animacion(
    [
        P.link(
            x1=a,
            x2=b,
            y1=f_cubica(a),
            y2=f_cubica(b),
            since=inicio,
            stroke=COLOR,
            strokeOpacity=0.2,
            clip=True,
        ),
        P.dot(
            x=x_f,
            y=np.zeros(N_FALSA),
            since=inicio,
            r=2.5,
            fill=COLOR,
            fillOpacity=0.4,
            clip=True,
        ),
        P.link(
            x1=a[pasos, None],
            x2=b[pasos, None],
            y1=f_cubica(a)[pasos, None],
            y2=f_cubica(b)[pasos, None],
            stroke=COLOR,
            strokeWidth=1.5,
            clip=True,
        ),
        P.link(
            x1=x_f[pasos, None],
            x2=x_f[pasos, None],
            y1=[0.0],
            y2=f_cubica(x_f)[pasos, None],
            stroke=COLOR,
            strokeDasharray="2 3",
            clip=True,
        ),
        P.dot(x=x_f[pasos, None], y=[0.0], r=4.5, fill=COLOR, clip=True, **CONTORNO),
    ],
    pasos,
    dominios,
    x_f,
    e_f,
    "Falsa posición, f(x) = x³ + 5x² + 2",
)
```

```python hidden
e_n = errores["Newton ($x_0=-6$)"]


def potencia(e):
    """El orden de magnitud de e, en LaTeX."""
    return rf"10^{{{int(np.floor(np.log10(e)))}}}"


md(
    rf"""**Newton.** La tangente en $(x_{{k-1}},f(x_{{k-1}}))$ corta el eje en $x_k$.
Cerca de la raíz el error se eleva al cuadrado en cada paso: $e_2\sim{potencia(e_n[1])}$,
$e_3\sim{potencia(e_n[2])}$, $e_4\sim{potencia(e_n[3])}$. En el último paso la
ventana deja de achicarse, porque $e_5$ ya es del orden del redondeo de
`float64`."""
)
```

```python hidden
N_NEWTON = 5
recorridos = np.concatenate([[-6.0], historias["Newton ($x_0=-6$)"]])
antes, x_n = recorridos[:N_NEWTON], recorridos[1 : N_NEWTON + 1]
pasos, dominios = recorrido(x_n, np.maximum(3 * e_n[:N_NEWTON], 2e-9))
inicio = np.arange(N_NEWTON) * INICIO
COLOR = "var(--chart-3)"
animacion(
    [
        P.link(
            x1=antes,
            x2=x_n,
            y1=f_cubica(antes),
            y2=np.zeros(N_NEWTON),
            since=inicio,
            stroke=COLOR,
            strokeOpacity=0.2,
            clip=True,
        ),
        P.dot(
            x=x_n,
            y=np.zeros(N_NEWTON),
            since=inicio,
            r=2.5,
            fill=COLOR,
            fillOpacity=0.4,
            clip=True,
        ),
        P.link(
            x1=antes[pasos, None],
            x2=x_n[pasos, None],
            y1=f_cubica(antes)[pasos, None],
            y2=[0.0],
            stroke=COLOR,
            strokeWidth=1.5,
            clip=True,
        ),
        P.dot(
            x=antes[pasos, None],
            y=f_cubica(antes)[pasos, None],
            r=3,
            fill=COLOR,
            clip=True,
        ),
        P.dot(x=x_n[pasos, None], y=[0.0], r=4.5, fill=COLOR, clip=True, **CONTORNO),
    ],
    pasos,
    dominios,
    x_n,
    e_n,
    "Newton desde x₀ = −6, f(x) = x³ + 5x² + 2",
)
```

```python hidden
ETIQUETAS = {
    "bisección": "bisección",
    "falsa posición": "falsa posición",
    "Newton ($x_0=-6$)": "Newton, x₀ = −6",
}
EPS = np.finfo(float).eps


def serie_log(e, nombre, **opciones):
    """Iteración contra error, sin los ceros que el eje log no puede mostrar."""
    k = np.arange(1, len(e) + 1)
    return P.line(x=k[e > 0], y=e[e > 0], series=nombre, **opciones)


P.figure(
    *(serie_log(e, ETIQUETAS[n], marker="dot") for n, e in errores.items()),
    serie_log(
        anchos_biseccion, "cota de la bisección, (b−a)/2ᵏ⁺¹", strokeDasharray="1 3"
    ),
    P.ruleY([EPS], strokeDasharray="4 3", strokeOpacity=0.6),
    P.text(x=[1], y=[EPS], text=["ε"], textAnchor="start", dx=6, dy=-8),
    title="Error de cada método, f(x) = x³ + 5x² + 2",
    x={"label": "iteración k"},
    y={"type": "log", "domain": [1e-17, 10], "label": "|xₖ − x*|"},
    grid=True,
)
```

```python hidden
def primero(e, tol):
    k = np.flatnonzero(e < tol)
    return str(k[0] + 1) if len(k) else "no llega"


tols = (1e-4, 1e-8, 1e-12)
filas = [
    f"| {ETIQUETAS[n]} | " + " | ".join(primero(e, t) for t in tols) + " |"
    for n, e in errores.items()
]
filas.append(
    "| bisección, cota | "
    + " | ".join(primero(anchos_biseccion, t) for t in tols)
    + " |"
)
md(
    "\n".join(
        [
            "Primera iteración con error real menor que la tolerancia:",
            "",
            "| método | $10^{-4}$ | $10^{-8}$ | $10^{-12}$ |",
            "|---|---:|---:|---:|",
            *filas,
        ]
    )
)
```

El error real de la bisección no baja de forma monótona (la raíz puede quedar
cerca de un punto medio por azar), pero la cota sí, y es lo que se garantiza.
Falsa posición baja casi como una recta, más rápido que la bisección. Newton lo
hace en 5 pasos.

## Orden de convergencia observado

Si $e_{k+1}\approx C\,e_k^{\,p}$ entonces
$p\approx\dfrac{\ln(e_{k+1}/e_k)}{\ln(e_k/e_{k-1})}$. En una gráfica de
$e_{k+1}$ contra $e_k$ en escala logarítmica, $p$ es la pendiente. Solo se usan
los errores mayores que $10^{-14}$, antes de que el redondeo de `float64`
domine. Para la bisección se usa la cota, que es la que se reduce exactamente a
la mitad.

```python
series = {
    "bisección (cota)": anchos_biseccion,
    "falsa posición": errores["falsa posición"],
    "Newton ($x_0=-6$)": errores["Newton ($x_0=-6$)"],
}
ordenes = {}
razones = {}
for nombre, e in series.items():
    e = e[e > 1e-14]
    ordenes[nombre] = np.log(e[2:] / e[1:-1]) / np.log(e[1:-1] / e[:-2])
    razones[nombre] = e[1:] / e[:-1]
series_validas = {n: e[e > 1e-14] for n, e in series.items()}
```

```python hidden
ETIQUETAS["bisección (cota)"] = "bisección (cota)"
P.figure(
    *(
        P.line(x=e[:-1], y=e[1:], series=ETIQUETAS[n], marker="dot")
        for n, e in series_validas.items()
    ),
    P.line(x=[1e-14, 1], y=[1e-14, 1], series="eₖ₊₁ = eₖ", strokeDasharray="1 3"),
    title="La pendiente es p",
    x={"type": "log", "label": "eₖ"},
    y={"type": "log", "label": "eₖ₊₁"},
    grid=True,
)
```

```python hidden
md(
    "\n".join(
        [
            "| método | $p$ (mediana) | $e_{k+1}/e_k$ al final |",
            "|---|---:|---:|",
            *[
                f"| {ETIQUETAS[n]} | {np.median(ordenes[n]):.2f} | {razones[n][-1]:.3f} |"
                for n in ordenes
            ],
        ]
    )
)
```

La bisección y falsa posición dan $p=1$ (convergencia lineal) con razones $0.5$
y $\approx0.28$: la segunda es una constante de la función y el intervalo, la
primera no depende de ellos. Newton da $p=2$ y las razones $e_{k+1}/e_k$ no se
estabilizan: tienden a cero.

En falsa posición uno de los extremos queda fijo en todas las iteraciones (la
función es cóncava en el intervalo y la cuerda siempre corta del mismo lado),
así que el intervalo no se achica y el criterio $|b-a|<\tau$ de la bisección no
sirve; se mide $|f|$ o el cambio entre iterados.

## Cuando Newton falla o pierde el orden

**Punto inicial.** Con el mismo $f$ y $x_0=-1$ se tiene $f(-1)=6$ y $f'(-1)=-7$,
así que $x_1=-1-6/(-7)\approx-0.143$: el primer paso cae cerca de $x=0$, donde
$f'=0$ y las tangentes son casi horizontales, y los iterados siguientes saltan
sin acercarse a la raíz. Con $x_0=-6$ converge en 5 pasos. Newton no exige un
corchete y por eso no garantiza nada lejos de la raíz.

**Raíz múltiple.** Si $f(x)=(x-1)^2(x+2)$, la raíz $x=1$ es doble: $f'(1)=0$ y
la convergencia baja a lineal con razón $\tfrac12$. Para una raíz de
multiplicidad $m$, $x_{k+1}=x_k-m\,f(x_k)/f'(x_k)$ recupera el orden 2.

```python
iterados_malos = newton(f_cubica, df_cubica, -1.0, 40)
n_cerca = int(np.sum(np.abs(iterados_malos - float(RAIZ)) < 1e-6))


def f_doble(x):
    return (x - 1) ** 2 * (x + 2)


def df_doble(x):
    return (x - 1) * (3 * x + 3)


error_doble = {
    "Newton clásico": np.abs(newton(f_doble, df_doble, 2.0, 14) - 1),
    "Newton con $m=2$": np.abs(newton(f_doble, df_doble, 2.0, 14, 2) - 1),
}
```

```python hidden
md(
    f"Desde $x_0=-1$, de los 40 iterados de Newton, {n_cerca} quedan a menos de "
    f"$10^{{-6}}$ de la raíz. Primer iterado: $x_1={iterados_malos[0]:.4f}$. "
    f"El iterado más cercano a $x=0$ está a {np.min(np.abs(iterados_malos)):.3f}."
)
```

```python hidden
P.figure(
    serie_log(error_doble["Newton clásico"], "Newton clásico", marker="dot"),
    serie_log(error_doble["Newton con $m=2$"], "Newton con m = 2", marker="dot"),
    title="Raíz doble de f(x) = (x − 1)²(x + 2), x₀ = 2",
    x={"label": "iteración k"},
    y={"type": "log", "label": "|xₖ − 1|"},
    grid=True,
)
```

```python hidden
e = error_doble["Newton clásico"]
md(
    f"""
    Con la raíz doble el error de Newton clásico se reduce a la mitad en cada
    paso (de {e[0]:.2e} a {e[-1]:.2e} en 14 pasos, razón {e[-1] / e[-2]:.3f}).
    Con $m=2$ el error cae a cero (se anula en `float64`) en 5 pasos. El precio
    es saber $m$ de antemano.
    """
)
```
