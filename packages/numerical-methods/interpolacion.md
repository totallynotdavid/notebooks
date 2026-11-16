```python hidden
from math import factorial

import numpy as np
from quire import md
from quire import plot as P
```

# Interpolación polinomial

Dados $n+1$ puntos $(x_i,y_i)$ con $x_i$ distintos, existe un único polinomio
$p$ de grado $\le n$ con $p(x_i)=y_i$. Hay varias formas de escribirlo; todas
dan el mismo polinomio (en aritmética exacta) y difieren en el costo y en cómo
se actualizan cuando llega un punto nuevo.

| forma    | expresión                                                               | punto nuevo          |
| -------- | ----------------------------------------------------------------------- | -------------------- |
| Lagrange | $p(x)=\sum_i y_i L_i(x)$, $L_i(x)=\prod_{j\ne i}\dfrac{x-x_j}{x_i-x_j}$ | se recalcula todo    |
| Newton   | $p(x)=\sum_k [x_0,\ldots,x_k]\prod_{j<k}(x-x_j)$                        | se agrega un término |

```python
def lagrange(x, y, t):
    """Valor en t del polinomio de Lagrange que pasa por (x, y)."""
    t = np.asarray(t, dtype=float)
    total = np.zeros_like(t)
    for i in range(len(x)):
        base = np.ones_like(t)
        for j in range(len(x)):
            if i != j:
                base *= (t - x[j]) / (x[i] - x[j])
        total += y[i] * base
    return total


def diferencias_divididas(x, y):
    """Columnas de la tabla de diferencias divididas.

    La columna j tiene n - j entradas: [x_i, ..., x_{i+j}] para i = 0...
    """
    x = np.asarray(x, dtype=float)
    columnas = [np.asarray(y, dtype=float)]
    for j in range(1, len(x)):
        previa = columnas[-1]
        columnas.append((previa[1:] - previa[:-1]) / (x[j:] - x[: len(x) - j]))
    return columnas


def newton(x, y, t, terminos=None):
    """Polinomio de Newton en t con `terminos` coeficientes (todos si None)."""
    coef = [c[0] for c in diferencias_divididas(x, y)][:terminos]
    resultado = np.full_like(np.asarray(t, dtype=float), coef[-1])
    for k in range(len(coef) - 2, -1, -1):
        resultado = resultado * (t - x[k]) + coef[k]
    return resultado
```

## Lagrange con cuatro puntos

Datos $x=1,2,3,4$ con $y=0.671,\ 0.620,\ 0.567,\ 0.520$, interpolados en
$x=2.8$. Cada $L_i$ vale 1 en $x_i$ y 0 en los demás nodos.

```python
X_L = np.array([1.0, 2.0, 3.0, 4.0])
Y_L = np.array([0.671, 0.620, 0.567, 0.520])
valor_lagrange = float(lagrange(X_L, Y_L, np.array(2.8)))
pesos = [float(lagrange(X_L, np.eye(4)[i], np.array(2.8))) for i in range(4)]
md(
    "\n".join(
        [
            "| $i$ | $x_i$ | $y_i$ | $L_i(2.8)$ | $y_iL_i(2.8)$ |",
            "|---:|---:|---:|---:|---:|",
            *[
                f"| {i} | {X_L[i]:.0f} | {Y_L[i]:.3f} | {pesos[i]:+.4f} | {Y_L[i] * pesos[i]:+.5f} |"
                for i in range(4)
            ],
        ]
    )
)
```

```python hidden
md(
    f"$p(2.8)=\\sum_i y_iL_i(2.8)={valor_lagrange:.5f}$. "
    f"Los $L_i(2.8)$ suman {sum(pesos):.1f}."
)
```

```python hidden
t = np.linspace(0.8, 4.2, 300)
P.grid(
    P.figure(
        *(
            P.line(x=t, y=lagrange(X_L, np.eye(4)[i], t), series=f"L{'₀₁₂₃'[i]}")
            for i in range(4)
        ),
        P.ruleY([0]),
        title="Polinomios de la base de Lagrange",
        x={"label": "x"},
        grid=True,
    ),
    P.figure(
        P.line(x=t, y=lagrange(X_L, Y_L, t), series="p(x)"),
        P.dot(x=X_L, y=Y_L, r=4, series="datos"),
        P.dot(x=[2.8], y=[valor_lagrange], r=6, series="p(2.8)"),
        title="Polinomio interpolante",
        x={"label": "x"},
        grid=True,
    ),
)
```

## Newton: diferencias divididas

$[x_i]=y_i$ y
$[x_i,\ldots,x_{i+j}]=\dfrac{[x_{i+1},\ldots,x_{i+j}]-[x_i,\ldots,x_{i+j-1}]}{x_{i+j}-x_i}$.
El polinomio usa la primera fila de la tabla. Los datos son $J_0(x)$, la función
de Bessel de primera especie y orden 0, con 5 decimales, en siete nodos no
equiespaciados. Se interpola en $x=0.28$ y el valor verdadero se calcula con la
serie $J_0(x)=\sum_k\frac{(-1)^k}{(k!)^2}(x/2)^{2k}$.

```python
X_N = np.array([0.1, 0.2, 0.4, 0.7, 1.0, 1.2, 1.3])
Y_N = np.array([0.99750, 0.99002, 0.96040, 0.88122, 0.76520, 0.67113, 0.62009])


def bessel_j0(x):
    return sum((-1) ** k * (x / 2) ** (2 * k) / factorial(k) ** 2 for k in range(20))


tabla = diferencias_divididas(X_N, Y_N)
filas = []
for i in range(len(X_N)):
    celdas = [f"{tabla[j][i]:.5f}" for j in range(len(X_N) - i)]
    celdas += [""] * (len(X_N) - len(celdas))
    filas.append(f"| {X_N[i]:.1f} | " + " | ".join(celdas) + " |")
cabecera = "| $x_i$ | " + " | ".join(f"$j={j}$" for j in range(len(X_N))) + " |"
md("\n".join([cabecera, "|---:|" + "---:|" * len(X_N), *filas]))
```

```python
exacto = bessel_j0(0.28)
parciales = [float(newton(X_N, Y_N, np.array(0.28), terminos=m)) for m in range(1, 8)]
md(
    "\n".join(
        [
            f"$J_0(0.28)={exacto:.7f}$. Sumando un término de Newton a la vez:",
            "",
            "| términos | grado | $p(0.28)$ | error |",
            "|---:|---:|---:|---:|",
            *[
                f"| {m + 1} | {m} | {p:.7f} | {abs(p - exacto):.1e} |"
                for m, p in enumerate(parciales)
            ],
        ]
    )
)
```

Desde el grado 4 el error es del orden de $5\times10^{-6}$, el mismo que el
redondeo de los datos a 5 decimales (hasta $5\times10^{-6}$ por dato): ya no
mejora con más nodos. Cada fila agrega un término sin tocar los anteriores. En
la forma de Lagrange habría que recalcular todos los $L_i$.

Que Lagrange y Newton son el mismo polinomio se comprueba evaluando ambos en una
malla:

```python
t = np.linspace(0.1, 1.3, 500)
diferencia = np.max(np.abs(lagrange(X_N, Y_N, t) - newton(X_N, Y_N, t)))
md(
    f"Máxima diferencia entre Lagrange y Newton sobre $[0.1,1.3]$: "
    f"{diferencia:.1e}, es decir, redondeo de `float64`."
)
```

## Nodos equiespaciados: diferencias finitas

Con paso $h$ constante, $[x_i,\ldots,x_{i+j}]=\Delta^jf_i/(j!\,h^j)$ y el
polinomio queda en términos de las diferencias finitas. Con $s=(x-x_0)/h$, hacia
adelante

$$
p(x)=\sum_{k=0}^n\binom sk\Delta^kf_0,\qquad
\binom sk=\frac{s(s-1)\cdots(s-k+1)}{k!},
$$

y con $s=(x-x_n)/h$, hacia atrás (con $\nabla f_i=f_i-f_{i-1}$)

$$
p(x)=\sum_{k=0}^n\binom{s+k-1}{k}\nabla^kf_n .
$$

Dos tablas con paso constante. La primera, $x=150,160,\ldots,210$ con
$y=35.5,37.8,43.6,45.7,47.3,50.1,51.2$, se interpola en $x=162$ con la fórmula
hacia adelante. La segunda, $x=500,700,\ldots,1900$ con
$y=365,361.6,370.74,379.68,384.46,395.5,395.95,397$, se interpola en $x=1000$
con la fórmula hacia atrás. Ambas se comparan con las diferencias divididas.

```python
def binomial_generalizado(s, k):
    """s (s - 1) ... (s - k + 1) / k!"""
    resultado = 1.0
    for i in range(k):
        resultado *= (s - i) / (i + 1)
    return resultado


def tabla_diferencias(y):
    columnas = [np.asarray(y, dtype=float)]
    while len(columnas[-1]) > 1:
        columnas.append(np.diff(columnas[-1]))
    return columnas


def newton_adelante(x0, h, y, xi):
    s = (xi - x0) / h
    tabla = tabla_diferencias(y)
    return sum(binomial_generalizado(s, k) * tabla[k][0] for k in range(len(tabla)))


def newton_atras(xn, h, y, xi):
    s = (xi - xn) / h
    tabla = tabla_diferencias(y)
    return sum(
        binomial_generalizado(s + k - 1, k) * tabla[k][-1] for k in range(len(tabla))
    )


x_a = 150.0 + 10.0 * np.arange(7)
y_a = np.array([35.5, 37.8, 43.6, 45.7, 47.3, 50.1, 51.2])
x_b = 500.0 + 200.0 * np.arange(8)
y_b = np.array([365.0, 361.6, 370.74, 379.68, 384.46, 395.5, 395.95, 397.0])
adelante = newton_adelante(x_a[0], 10.0, y_a, 162.0)
atras = newton_atras(x_b[-1], 200.0, y_b, 1000.0)
dd_a = float(newton(x_a, y_a, np.array(162.0)))
dd_b = float(newton(x_b, y_b, np.array(1000.0)))
```

La tabla de diferencias hacia adelante de la primera serie:

```python hidden
diferencias = tabla_diferencias(y_a)
n = len(y_a)
filas = [
    f"| {i} | "
    + " | ".join(f"{diferencias[j][i]:.2f}" if i < n - j else "" for j in range(n))
    + " |"
    for i in range(n)
]
md(
    "\n".join(
        [
            "| $i$ | " + " | ".join(f"$\\Delta^{j}$" for j in range(n)) + " |",
            "|---:|" + "---:|" * n,
            *filas,
        ]
    )
)
```

```python hidden
md(
    "\n".join(
        [
            "| serie | fórmula | $x$ | $p(x)$ | diferencias divididas |",
            "|---|---|---:|---:|---:|",
            f"| 1 | adelante | 162 | {adelante:.6f} | {dd_a:.6f} |",
            f"| 2 | atrás | 1000 | {atras:.6f} | {dd_b:.6f} |",
        ]
    )
)
```

Las dos formas coinciden hasta el redondeo. La de adelante construye el
polinomio desde el primer nodo y la de atrás desde el último, y sirven para
interpolar cerca de ese extremo de la tabla. En la tabla de diferencias de la
primera serie, $\Delta^k$ no decrece con $k$ (2.3, 3.5, $-7.2$, 10.4, $-11.9$,
8.8): los datos tienen ruido, y el polinomio de grado 6 que pasa por todos ellos
lo incorpora. Truncar la serie en un orden bajo suele dar un valor más razonable
que usar todos los nodos.

## El fenómeno de Runge

Más nodos no significa mejor aproximación. El error de interpolación es

$$
f(x)-p(x)=\frac{f^{(n+1)}(\xi)}{(n+1)!}\prod_{i=0}^n(x-x_i),
$$

y el producto depende solo de los nodos. Para nodos equiespaciados es pequeño en
el centro y grande cerca de los extremos. Con $f(x)=\dfrac1{1+25x^2}$ en
$[-1,1]$, las derivadas crecen tan rápido (hay polos en $x=\pm i/5$) que el
error crece con el grado. Los nodos de Chebyshev,
$x_i=\cos\frac{(2i+1)\pi}{2(n+1)}$, se agrupan hacia los extremos y hacen
pequeño el producto.

```python
def runge(x):
    return 1.0 / (1.0 + 25.0 * x**2)


def nodos_equiespaciados(n):
    return np.linspace(-1.0, 1.0, n + 1)


def nodos_chebyshev(n):
    return np.cos((2 * np.arange(n + 1) + 1) * np.pi / (2 * (n + 1)))


MALLA = np.linspace(-1.0, 1.0, 4001)
GRADOS = np.arange(2, 41, 2)


def error_maximo(nodos, n, malla):
    x = nodos(n)
    return np.max(np.abs(lagrange(x, runge(x), malla) - runge(malla)))


errores_runge = {
    "equiespaciados": np.array(
        [error_maximo(nodos_equiespaciados, n, MALLA) for n in GRADOS]
    ),
    "Chebyshev": np.array([error_maximo(nodos_chebyshev, n, MALLA) for n in GRADOS]),
}
centro = MALLA[np.abs(MALLA) <= 0.5]
errores_centro = np.array(
    [error_maximo(nodos_equiespaciados, n, centro) for n in GRADOS]
)
```

Mueve el grado: con nodos equiespaciados el polinomio oscila cada vez más cerca
de los extremos, y con nodos de Chebyshev se acerca a la función.

```python hidden
RHO = (1 + np.sqrt(26)) / 5
malla = MALLA[::10]
grados = GRADOS[GRADOS <= 20]


def nodos_rellenos(n):
    """Los nodos equiespaciados de grado n, completados con NaN hasta el mayor grado."""
    x = np.full(grados[-1] + 1, np.nan)
    x[: n + 1] = nodos_equiespaciados(n)
    return x


P.grid(
    P.figure(
        P.line(x=malla, y=runge(malla), series="1/(1+25x²)", strokeWidth=2.5),
        *(
            P.line(
                x=malla,
                y=np.array(
                    [lagrange(nodos(n), runge(nodos(n)), malla) for n in grados]
                ),
                series=nombre,
                clip=True,
            )
            for nombre, nodos in (
                ("equiespaciados", nodos_equiespaciados),
                ("Chebyshev", nodos_chebyshev),
            )
        ),
        P.dot(
            x=np.array([nodos_rellenos(n) for n in grados]),
            y=np.array([runge(nodos_rellenos(n)) for n in grados]),
            r=3,
            series="nodos equiespaciados",
        ),
        frames=[f"n = {n}" for n in grados],
        parameter="grado",
        start=int(np.flatnonzero(grados == 14)[0]),
        title="Polinomio interpolante",
        x={"label": "x"},
        y={"domain": [-0.6, 1.4]},
        grid=True,
    ),
    P.figure(
        *(
            P.line(x=GRADOS, y=e, series=nombre, marker="dot")
            for nombre, e in errores_runge.items()
        ),
        P.line(
            x=GRADOS,
            y=errores_runge["Chebyshev"][-1] * RHO ** (GRADOS[-1] - GRADOS),
            series="ρ⁻ⁿ, ρ = (1+√26)/5",
            strokeDasharray="1 3",
        ),
        title="Error máximo en [−1, 1]",
        x={"label": "grado n"},
        y={"type": "log"},
        grid=True,
    ),
)
```

El error máximo sobre una malla de 4001 puntos, con nodos equiespaciados en
$[-1,1]$ y en el centro $[-0.5,0.5]$, y con nodos de Chebyshev en $[-1,1]$:

```python hidden
indice = {int(n): k for k, n in enumerate(GRADOS)}
md(
    "\n".join(
        [
            "| grado $n$ | equiespaciados | centro | Chebyshev |",
            "|---:|---:|---:|---:|",
            *[
                f"| {n} | {errores_runge['equiespaciados'][indice[n]]:.1e} "
                f"| {errores_centro[indice[n]]:.1e} "
                f"| {errores_runge['Chebyshev'][indice[n]]:.1e} |"
                for n in (6, 10, 20, 30, 40)
            ],
        ]
    )
)
```

Con nodos equiespaciados el error en $[-1,1]$ crece con $n$ (las oscilaciones
cerca de $x=\pm1$ de la gráfica izquierda), pero en el centro, $|x|\le0.5$,
sigue bajando. Con nodos de Chebyshev el error baja geométricamente, con la
razón $\rho^{-1}$ que fija la distancia de los polos de $f$ al intervalo. La
causa está en los nodos, no en la función ni en la aritmética: interpolar con
polinomios de grado alto en nodos equiespaciados es una mala idea aunque no haya
error de redondeo.
