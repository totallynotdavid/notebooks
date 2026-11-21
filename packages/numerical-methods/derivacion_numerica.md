```python hidden
import numpy as np
from quire import md
from quire import plot as P
```

# Derivación numérica

Se aproxima $f'(x)$ con valores de $f$ en puntos cercanos. Todas las fórmulas
salen del desarrollo de Taylor
$f(x+h)=f(x)+hf'(x)+\tfrac{h^2}{2}f''(x)+\tfrac{h^3}{6}f'''(x)+\cdots$

| fórmula           | expresión                            | error de truncamiento            |
| ----------------- | ------------------------------------ | -------------------------------- |
| adelante          | $\dfrac{f(x+h)-f(x)}{h}$             | $+\tfrac h2 f''(x)+O(h^2)$       |
| atrás             | $\dfrac{f(x)-f(x-h)}{h}$             | $-\tfrac h2 f''(x)+O(h^2)$       |
| centrada          | $\dfrac{f(x+h)-f(x-h)}{2h}$          | $+\tfrac{h^2}{6} f'''(x)+O(h^4)$ |
| 3 puntos adelante | $\dfrac{-3f(x)+4f(x+h)-f(x+2h)}{2h}$ | $-\tfrac{h^2}{3} f'''(x)+O(h^3)$ |
| 3 puntos atrás    | $\dfrac{3f(x)-4f(x-h)+f(x-2h)}{2h}$  | $-\tfrac{h^2}{3} f'''(x)+O(h^3)$ |

El error es $D-f'$, y la tabla muestra su primer término. El ejemplo es
$f(x)=\tan x$ en $x=1$, con $f'(x)=\sec^2 x$. Todos los cálculos usan doble
precisión (`float64`).

```python
X0 = 1.0
f = np.tan


def derivada_exacta(x):
    return 1.0 / np.cos(x) ** 2


def adelante(f, x, h):
    return (f(x + h) - f(x)) / h


def atras(f, x, h):
    return (f(x) - f(x - h)) / h


def centrada(f, x, h):
    return (f(x + h) - f(x - h)) / (2 * h)


def adelante_3(f, x, h):
    return (-3 * f(x) + 4 * f(x + h) - f(x + 2 * h)) / (2 * h)


def atras_3(f, x, h):
    return (3 * f(x) - 4 * f(x - h) + f(x - 2 * h)) / (2 * h)


formulas = {
    "atrás": atras,
    "adelante": adelante,
    "centrada": centrada,
    "3 puntos atrás": atras_3,
    "3 puntos adelante": adelante_3,
}
exacta = derivada_exacta(X0)
```

## Valores para $h=0.1,\ 0.05,\ 0.02$

```python hidden
md(f"$f'(1)=\\sec^2 1={exacta:.6f}$. El error es $100\\,(f'-D)/f'$.")
```

```python
filas = []
for h in (0.1, 0.05, 0.02):
    for nombre, formula in formulas.items():
        d = formula(f, X0, h)
        filas.append(
            f"| {h} | {nombre} | {d:.6f} | {100 * (exacta - d) / exacta:.4f} |"
        )
md("\n".join(["| $h$ | fórmula | $D$ | error (%) |", "|---|---|---:|---:|", *filas]))
```

```python hidden
def cociente(nombre):
    formula = formulas[nombre]
    return (formula(f, X0, 0.1) - exacta) / (formula(f, X0, 0.05) - exacta)


orden_1 = [cociente(n) for n in ("atrás", "adelante")]
orden_2 = [cociente(n) for n in ("centrada", "3 puntos atrás", "3 puntos adelante")]
md(
    rf"""
    Al pasar de $h=0.1$ a $0.05$ el error de las fórmulas de orden 1 se divide
    entre {min(orden_1):.2f} y {max(orden_1):.2f}, y el de las de orden 2 entre
    {min(orden_2):.2f} y {max(orden_2):.2f}. El orden $p$ predice $2^p$, es
    decir 2 y 4, cuando $e(h)\approx C\,h^p$. Con $h=0.1$ los términos siguientes
    del desarrollo aún pesan, sobre todo en las fórmulas de 3 puntos, cuyo
    siguiente término es $O(h^3)$; en la gráfica de abajo las pendientes se
    miden con $h$ menores.
    """
)
```

## Error contra $h$: el orden y el piso del redondeo

Reducir $h$ no mejora la derivada sin límite. El numerador $f(x+h)-f(x)$ resta
dos números casi iguales y pierde cifras. Cada valor de $f$ tiene un error
relativo de hasta $\varepsilon/2$ (con $\varepsilon=2^{-52}$ el épsilon de
máquina de `float64`), así que el numerador tiene un error absoluto del orden de
$\varepsilon\,|f|$, que al dividir entre $h$ da

$$
e(h)\;\approx\;\underbrace{C\,h^p}_{\text{truncamiento}}
\;+\;\underbrace{\frac{\varepsilon\,|f(x)|}{h}}_{\text{redondeo}} .
$$

El truncamiento baja con $h$ y el redondeo sube. El mínimo está en
$h\sim\varepsilon^{1/(p+1)}$: $\approx10^{-8}$ para $p=1$ y $\approx10^{-5}$
para $p=2$.

```python
H = np.logspace(-1, -16, 151)
errores = {
    "adelante": np.abs(adelante(f, X0, H) - exacta),
    "centrada": np.abs(centrada(f, X0, H) - exacta),
    "3 puntos adelante": np.abs(adelante_3(f, X0, H) - exacta),
}


def pendiente(nombre, h_max, h_min):
    """Pendiente de log e contra log h en h_min <= h <= h_max."""
    tramo = (h_max >= H) & (h_min <= H)
    return np.polyfit(np.log10(H[tramo]), np.log10(errores[nombre][tramo]), 1)[0]


pendientes = {
    "adelante": pendiente("adelante", 1e-3, 1e-6),
    "centrada": pendiente("centrada", 1e-2, 1e-4),
    "3 puntos adelante": pendiente("3 puntos adelante", 1e-2, 1e-4),
}
h_optimo = {nombre: H[e.argmin()] for nombre, e in errores.items()}
e_minimo = {nombre: e.min() for nombre, e in errores.items()}

# Modelo e(h) = C h^p + eps |f| / h con las derivadas de tan en x = 1:
# f'' = 2t(1+t^2), f''' = 2(1+t^2)(1+3t^2), t = tan x.
t = np.tan(X0)
EPS = np.finfo(float).eps
c1 = abs(2 * t * (1 + t**2)) / 2
c2 = abs(2 * (1 + t**2) * (1 + 3 * t**2)) / 6
h_modelo = {
    "adelante": np.sqrt(EPS * abs(t) / c1),
    "centrada": (EPS * abs(t) / (2 * c2)) ** (1 / 3),
}
e_modelo = {
    "adelante": c1 * h_modelo["adelante"] + EPS * abs(t) / h_modelo["adelante"],
    "centrada": c2 * h_modelo["centrada"] ** 2 + EPS * abs(t) / h_modelo["centrada"],
}
```

```python hidden
P.figure(
    *(
        P.line(x=H[e > 0], y=e[e > 0], series=nombre, marker="dot", clip=True)
        for nombre, e in errores.items()
    ),
    P.line(
        x=H, y=EPS * abs(f(X0)) / H, series="ε|f|/h", strokeDasharray="1 3", clip=True
    ),
    P.line(x=H, y=2 * H, series="∝ h", strokeDasharray="6 3", clip=True),
    P.line(x=H, y=5 * H**2, series="∝ h²", strokeDasharray="6 3 1 3", clip=True),
    title="Error de la derivada de tan x en x = 1",
    x={"label": "h", "type": "log"},
    y={"label": "|D − f′(1)|", "type": "log", "domain": [1e-13, 10]},
    grid=True,
)
```

La pendiente se ajusta en el tramo donde domina el truncamiento. El modelo es
$e(h)=C\,h^p+\varepsilon|f|/h$ con $C$ tomado de las derivadas de $\tan$ en
$x=1$. Las columnas medidas son el $h$ y el error del mínimo de cada curva; las
del modelo, el mínimo de $e(h)$.

```python hidden
filas = [
    f"| {n} | {pendientes[n]:.2f} | {h_optimo[n]:.1e} | {e_minimo[n]:.1e} "
    + (f"| {h_modelo[n]:.1e} | {e_modelo[n]:.1e} |" if n in h_modelo else "| | |")
    for n in pendientes
]
md(
    "\n".join(
        [
            "| fórmula | pendiente | $h$ medido | error medido | $h$ modelo | error modelo |",
            "|---|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

El mínimo medido es una sola muestra de una curva ruidosa: puede caer más abajo
o más arriba que el del modelo (los redondeos a veces se compensan), pero el
modelo da el orden de magnitud. A la izquierda del mínimo el error crece como
$1/h$ (pendiente $-1$) y se vuelve irregular: es ruido de redondeo. Las fórmulas
de orden 2 alcanzan un error mucho menor que la de orden 1, y lo hacen con un
$h$ mayor, donde el redondeo todavía es pequeño.

## Extrapolación de Richardson

Si el error de una fórmula $D(h)$ tiene la forma
$D(h)=f'+a_1h^{p_1}+a_2h^{p_2}+\cdots$, se combinan dos evaluaciones con pasos
$h$ y $h/2$ para eliminar el primer término:

$$
D_1(h)=D(h/2)+\frac{D(h/2)-D(h)}{2^{p_1}-1}
$$

tiene error $O(h^{p_2})$. Repetir con $D_1$ elimina el siguiente término. Para
la fórmula centrada los exponentes son $2,4,6,\ldots$ (solo potencias pares);
para la de adelante son $1,2,3,\ldots$. Con $D_{k,0}=D(h/2^k)$ y exponentes
$p_1<p_2<\cdots$,

$$
D_{k,m}=D_{k,m-1}+\frac{D_{k,m-1}-D_{k-1,m-1}}{2^{p_m}-1}.
$$

No se necesita derivar $f$ más de una vez: solo evaluar $f$ en más puntos.

```python
def richardson(formula, f, x, h, niveles, exponentes):
    """Tabla de Richardson: fila k usa los pasos h, h/2, ..., h/2**k.

    La columna m tiene error O(h**exponentes[m]). Las entradas de la
    derecha de la diagonal quedan en NaN.
    """
    d = np.full((niveles + 1, niveles + 1), np.nan)
    for k in range(niveles + 1):
        d[k, 0] = formula(f, x, h / 2**k)
    for m in range(1, niveles + 1):
        for k in range(m, niveles + 1):
            d[k, m] = d[k, m - 1] + (d[k, m - 1] - d[k - 1, m - 1]) / (
                2 ** exponentes[m - 1] - 1
            )
    return d


EXPONENTES_CENTRADA = [2, 4, 6, 8, 10]
EXPONENTES_ADELANTE = [1, 2, 3, 4, 5]
```

Con $h=0.2$ y 4 niveles el paso más chico es $h/16=0.0125$. Las tablas dan el
error absoluto $|D_{k,m}-f'(1)|$:

```python
H0 = 0.2
tablas = {
    "centrada": richardson(centrada, f, X0, H0, 4, EXPONENTES_CENTRADA),
    "adelante": richardson(adelante, f, X0, H0, 4, EXPONENTES_ADELANTE),
}
texto = []
for nombre, d in tablas.items():
    texto += [
        f"**{nombre}**",
        "",
        "| $k$ | $D_{k,0}$ | $D_{k,1}$ | $D_{k,2}$ | $D_{k,3}$ | $D_{k,4}$ |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for k in range(d.shape[0]):
        celdas = ["" if np.isnan(v) else f"{abs(v - exacta):.2e}" for v in d[k]]
        texto.append(f"| {k} | " + " | ".join(celdas) + " |")
    texto.append("")
md("\n".join(texto))
```

```python hidden
d = tablas["centrada"]
md(
    f"""
    En la fórmula centrada, con el mismo paso mínimo $h/16$, el error baja de
    {abs(d[4, 0] - exacta):.1e} en $D_{{4,0}}$ a {abs(d[4, 4] - exacta):.1e} en
    $D_{{4,4}}$. En la fórmula de adelante las primeras columnas ganan un orden
    cada una, pero las últimas mejoran cada vez menos: con $h=0.2$ el paso
    todavía es grande para $\\tan$ (la singularidad $\\pi/2$ está a
    {np.pi / 2 - X0:.2f} de $x=1$) y los términos de orden alto del error pesan.
    """
)
```

Este es el error contra $h$ de la fórmula centrada con uno y con dos niveles de
Richardson:

```python
h_rich = H[H > 1e-9]
filas = [richardson(centrada, f, X0, h, 2, EXPONENTES_CENTRADA) for h in h_rich]
error_rich = {
    "centrada": np.array([abs(d[0, 0] - exacta) for d in filas]),
    "1 nivel (orden 4)": np.array([abs(d[1, 1] - exacta) for d in filas]),
    "2 niveles (orden 6)": np.array([abs(d[2, 2] - exacta) for d in filas]),
}
tramo = (h_rich <= 0.2) & (h_rich >= 0.02)
pendientes_rich = {
    nombre: np.polyfit(np.log10(h_rich[tramo]), np.log10(e[tramo]), 1)[0]
    for nombre, e in error_rich.items()
}
```

```python hidden
P.figure(
    *(
        P.line(x=h_rich[e > 0], y=e[e > 0], series=nombre, marker="dot", clip=True)
        for nombre, e in error_rich.items()
    ),
    title="Richardson sobre la diferencia centrada",
    x={"label": "h (paso mayor)", "type": "log"},
    y={"label": "|D − f′(1)|", "type": "log", "domain": [1e-16, 10]},
    grid=True,
)
```

```python hidden
i = np.argmin(np.abs(h_rich - 1e-2))
filas = [
    f"| {n} | {pendientes_rich[n]:.2f} | {error_rich[n][i]:.1e} | {error_rich[n].min():.1e} |"
    for n in error_rich
]
md(
    "\n".join(
        [
            "| método | pendiente | error en $h=10^{-2}$ | error mínimo |",
            "|---|---:|---:|---:|",
            *filas,
        ]
    )
)
```

```python hidden
md(
    rf"""
    Las pendientes, ajustadas en $0.02\le h\le0.2$, son
    {", ".join(f"{p:.2f}" for p in pendientes_rich.values())}, cerca de los
    órdenes 2, 4 y 6. Richardson no cambia el redondeo, $\varepsilon|f|/h$, pero
    reduce el truncamiento, así que el mínimo se alcanza con un $h$ mayor, donde
    el redondeo es menor. Por eso el error mínimo baja.
    """
)
```

## Derivada a partir de una tabla de diferencias

Cuando $f$ está tabulada con paso constante $h$ se arma la tabla de diferencias
$\Delta^i f_j$ ($\Delta f_j=f_{j+1}-f_j$,
$\Delta^{i}f_j=\Delta^{i-1}f_{j+1}-\Delta^{i-1}f_j$). Sea $E$ el operador que
avanza un paso, $Ef(x)=f(x+h)$, de modo que $\Delta=E-1$. Por Taylor, $Ef=\sum_k
\frac{h^k}{k!}f^{(k)}=e^{h\,d/dx}f$, así que $h\,\frac{d}{dx}=\ln
E=\ln(1+\Delta)$. Desarrollar el logaritmo da la derivada en $x_j$ como la serie

$$
f'(x_j)\approx\frac1h\sum_{i=1}^{t}\frac{(-1)^{i+1}}{i}\,\Delta^i f_j ,
$$

truncada en el orden $t$. Con diferencias hacia atrás ($\nabla f_j=f_j-f_{j-1}$)
los signos desaparecen: $f'(x_j)\approx\frac1h\sum_{i=1}^{t}\frac1i\nabla^i
f_j$.

Con $t=1$ es la diferencia adelante (o atrás); con $t=2$ es la fórmula de 3
puntos. Cada orden agrega un punto a la fórmula y una potencia de $h$ al error.
Aquí $f=\tan x$ está tabulada con $h=0.02$ y con $h=0.1$. La derivada adelante
se calcula en $x=1$ con los puntos $1,1+h,\ldots$ y la derivada atrás con los
puntos $\ldots,1-h,1$.

```python
def tabla_diferencias(y):
    """Columnas i = 0..n-1 de las diferencias finitas de y (largo n - i)."""
    columnas = [np.asarray(y, dtype=float)]
    while len(columnas[-1]) > 1:
        columnas.append(np.diff(columnas[-1]))
    return columnas


def derivada_serie_adelante(y, h, t):
    """f' en el primer punto de y con la serie de diferencias hacia adelante."""
    tabla = tabla_diferencias(y)
    return sum((-1) ** (i + 1) * tabla[i][0] / i for i in range(1, t + 1)) / h


def derivada_serie_atras(y, h, t):
    """f' en el último punto de y con la serie de diferencias hacia atrás."""
    tabla = tabla_diferencias(y)
    return sum(tabla[i][-1] / i for i in range(1, t + 1)) / h
```

La tabla da el error $D-f'(1)$ según el orden de truncamiento $t$:

```python
ORDEN_MAX = 6
columnas = {}
for h in (0.02, 0.1):
    y_adelante = f(X0 + h * np.arange(ORDEN_MAX + 1))
    y_atras = f(X0 - h * np.arange(ORDEN_MAX, -1, -1))
    columnas[h] = [
        (
            derivada_serie_adelante(y_adelante, h, orden) - exacta,
            derivada_serie_atras(y_atras, h, orden) - exacta,
        )
        for orden in range(1, ORDEN_MAX + 1)
    ]
filas = [
    f"| {orden} | {columnas[0.02][orden - 1][0]:+.2e} | {columnas[0.02][orden - 1][1]:+.2e} "
    f"| {columnas[0.1][orden - 1][0]:+.2e} | {columnas[0.1][orden - 1][1]:+.2e} |"
    for orden in range(1, ORDEN_MAX + 1)
]
md(
    "\n".join(
        [
            "| $t$ | adelante, $h=0.02$ | atrás, $h=0.02$ | adelante, $h=0.1$ | atrás, $h=0.1$ |",
            "|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

Con $h=0.02$ el error decrece con cada término, cada vez más despacio, y las
diferencias hacia adelante alternan de signo. Con $h=0.1$ la serie hacia
adelante se aleja de la derivada: sus puntos llegan hasta $x=1.6$, más allá de
la singularidad de $\tan$ en $\pi/2\approx1.571$, y la serie solo sirve cuando
$h$ es pequeño frente a la escala en que $f$ cambia. La serie hacia atrás, que
usa puntos con $x\le1$, sí converge, pero más despacio que con $h=0.02$. Agregar
términos no reemplaza a reducir $h$.
