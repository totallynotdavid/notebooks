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

La animación avanza una iteración por cuadro. La bisección muestra el intervalo
que queda y su punto medio; falsa posición, la cuerda y su corte con el eje;
Newton, la tangente en $x_{k-1}$ y su corte $x_k$. Cada panel da el error de su
$x_k$.

```python hidden
K = 6
METODOS = ["bisección", "falsa posición", "Newton, x₀ = −6"]
ERRORES = dict(zip(METODOS, errores.values(), strict=True))
k = np.arange(1, K + 1)
newton_x = np.concatenate([[-6.0], historias["Newton ($x_0=-6$)"]])
medio, ancho = medios[:K], anchos_biseccion[:K]
a, b = intervalos_falsa[:K].T
corte = cortes[:K]
anterior, nuevo = newton_x[:K], newton_x[1 : K + 1]
xs = np.linspace(-6.2, -3.8, 121)


def columna(valores):
    """Un valor por cuadro, como canal animado de una sola marca."""
    return np.asarray(valores)[:, None]


def panel(metodo, n=1):
    return {"fx": [metodo] * n}


P.figure(
    P.line(
        x=np.tile(xs, 3),
        y=np.tile(f_cubica(xs), 3),
        fx=np.repeat(METODOS, len(xs)),
        z=np.repeat(METODOS, len(xs)),
        stroke="currentColor",
        strokeOpacity=0.45,
        clip=True,
    ),
    P.ruleY([0], strokeOpacity=0.6),
    P.link(
        x1=columna(medio - ancho),
        x2=columna(medio + ancho),
        y1=[0.0],
        y2=[0.0],
        strokeWidth=8,
        strokeOpacity=0.5,
        series=METODOS[0],
        **panel(METODOS[0]),
    ),
    P.link(
        x1=columna(medio),
        x2=columna(medio),
        y1=[0.0],
        y2=columna(f_cubica(medio)),
        strokeDasharray="2 3",
        series=METODOS[0],
        **panel(METODOS[0]),
    ),
    P.dot(x=columna(medio), y=[0.0], r=4, series=METODOS[0], **panel(METODOS[0])),
    P.link(
        x1=columna(a),
        x2=columna(b),
        y1=columna(f_cubica(a)),
        y2=columna(f_cubica(b)),
        series=METODOS[1],
        **panel(METODOS[1]),
    ),
    P.link(
        x1=columna(corte),
        x2=columna(corte),
        y1=[0.0],
        y2=columna(f_cubica(corte)),
        strokeDasharray="2 3",
        series=METODOS[1],
        **panel(METODOS[1]),
    ),
    P.dot(x=columna(corte), y=[0.0], r=4, series=METODOS[1], **panel(METODOS[1])),
    P.link(
        x1=columna(anterior),
        x2=columna(nuevo),
        y1=columna(f_cubica(anterior)),
        y2=[0.0],
        series=METODOS[2],
        **panel(METODOS[2]),
    ),
    P.dot(
        x=columna(anterior),
        y=columna(f_cubica(anterior)),
        r=3,
        series=METODOS[2],
        **panel(METODOS[2]),
    ),
    P.dot(x=columna(nuevo), y=[0.0], r=4, series=METODOS[2], **panel(METODOS[2])),
    P.text(
        x=[-6.15] * 3,
        y=[16.0] * 3,
        text=np.array(
            [[f"e{j} = {ERRORES[m][j - 1]:.1e}" for m in METODOS] for j in k]
        ),
        fx=METODOS,
        textAnchor="start",
    ),
    title="Una iteración por cuadro, f(x) = x³ + 5x² + 2",
    frames=[f"k = {j}" for j in k],
    fps=0.8,
    x={"domain": [-6.2, -3.8], "label": "x", "ticks": 3},
    y={"domain": [-36, 21], "label": "f(x)"},
    fx={"domain": METODOS, "label": None},
    color={"legend": False},
    grid=True,
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
