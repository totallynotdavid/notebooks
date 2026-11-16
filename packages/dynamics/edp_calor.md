```python hidden
import numpy as np
from quire import md
from quire import plot as P
```

# Ecuación de calor en una dimensión

Una barra de longitud $L$ con difusividad $\alpha$ evoluciona según

$$
\frac{\partial T}{\partial t}=\alpha\frac{\partial^2T}{\partial x^2},
\qquad
T(0,t)=0,\quad T(L,t)=T_b,\quad T(x,0)=0\ \ (0\le x<L).
$$

Hay una solución analítica. Con $T=T_b\,x/L+u$, $u$ cumple la ecuación con
extremos en cero y condición inicial $u(x,0)=-T_b\,x/L$, y el desarrollo en
senos da

$$
T(x,t)=T_b\frac{x}{L}+\sum_{n=1}^{\infty}
\frac{2T_b(-1)^n}{n\pi}\,
\sin\frac{n\pi x}{L}\;e^{-\alpha(n\pi/L)^2t}.
$$

Cada modo decae con su propia constante de tiempo. Para $t>0$ la serie converge
de inmediato, y la usamos como referencia exacta con 400 términos.

```python
ALFA, LARGO, T_BORDE, NODOS = 10.0, 10.0, 100.0, 21
x = np.linspace(0.0, LARGO, NODOS)
dx = x[1] - x[0]


def fourier(t, terminos=400):
    n = np.arange(1, terminos + 1)[:, None]
    coef = 2 * T_BORDE * (-1.0) ** n / (n * np.pi)
    modos = (
        coef
        * np.sin(n * np.pi * x / LARGO)
        * np.exp(-ALFA * (n * np.pi / LARGO) ** 2 * t)
    )
    return T_BORDE * x / LARGO + modos.sum(axis=0)
```

## Esquemas

Con $T_i^n\approx T(i\,\Delta x,\,n\,\Delta t)$ y el número

$$
r=\frac{\alpha\,\Delta t}{\Delta x^2}
$$

el **esquema explícito** (FTCS) es

$$
T_i^{n+1}=T_i^n+r\left(T_{i-1}^n-2T_i^n+T_{i+1}^n\right).
$$

Para el modo de Fourier de número de onda $k$, cada paso lo multiplica por
$1-4r\sin^2(k\Delta x/2)$. El modo más oscilante ($k\Delta x=\pi$) se multiplica
por $1-4r$, que tiene módulo mayor que 1 si $r>1/2$: ese modo crece en cada
paso. El esquema es estable sólo para $r\le1/2$, y con $r=1/2$ el modo más
oscilante no decae.

**Crank–Nicolson** promedia el laplaciano entre $n$ y $n+1$:

$$
T_i^{n+1}-\tfrac r2\,\delta^2T_i^{n+1}
=T_i^{n}+\tfrac r2\,\delta^2T_i^{n},
\qquad
\delta^2T_i=T_{i-1}-2T_i+T_{i+1}.
$$

Cada paso resuelve un sistema tridiagonal. El factor de amplificación
$\dfrac{1-2r\sin^2(k\Delta x/2)}{1+2r\sin^2(k\Delta x/2)}$ tiene módulo menor
que 1 para todo $r$, y el error de truncamiento es $O(\Delta t^2+\Delta x^2)$ en
lugar de $O(\Delta t+\Delta x^2)$.

```python
def condicion_inicial():
    T = np.zeros(NODOS)
    T[-1] = T_BORDE
    return T


def explicito(r, t_final):
    dt = r * dx**2 / ALFA
    pasos = round(t_final / dt)
    T = condicion_inicial()
    historia = [T.copy()]
    for _ in range(pasos):
        T[1:-1] += r * (T[:-2] - 2 * T[1:-1] + T[2:])
        historia.append(T.copy())
    return dt * np.arange(pasos + 1), np.array(historia)


def crank_nicolson(r, t_final):
    dt = r * dx**2 / ALFA
    pasos = round(t_final / dt)
    n = NODOS - 2
    laplaciano = (
        np.diag(-2.0 * np.ones(n))
        + np.diag(np.ones(n - 1), 1)
        + np.diag(np.ones(n - 1), -1)
    )
    izquierda = np.eye(n) - 0.5 * r * laplaciano
    derecha = np.eye(n) + 0.5 * r * laplaciano
    T = condicion_inicial()
    historia = [T.copy()]
    for _ in range(pasos):
        b = derecha @ T[1:-1]
        b[-1] += r * T_BORDE  # Mantiene fijo el extremo derecho en ambos pasos.
        T[1:-1] = np.linalg.solve(izquierda, b)
        historia.append(T.copy())
    return dt * np.arange(pasos + 1), np.array(historia)
```

## Explícito con $r=0.4$, $0.5$ y $0.6$

Fijamos $\alpha=10$, $L=10$, $T_b=100$ y $\Delta x=0.5$, y cambiamos $\Delta t$
para obtener cada $r$. Los tres casos avanzan hasta $t=1.5$.

```python
T_FINAL = 1.5
R_EXPLICITOS = (0.4, 0.5, 0.6)
explicitos = {r: explicito(r, T_FINAL) for r in R_EXPLICITOS}


def en_el_instante(t, T, instante):
    k = round(instante / (t[1] - t[0]))
    return t[k], T[k]
```

Cada panel muestra el perfil en cuatro instantes, y la línea fina sin puntos es
la solución de Fourier en el mismo instante. La escala vertical está recortada a
$[-20, 120]$; la anotación de cada panel da el valor real de $\max|T|$.

```python hidden
INSTANTES = (0.1, 0.3, 0.6, 1.5)
paneles = [f"r = {r}, Δt = {r * dx**2 / ALFA:.4f}" for r in R_EXPLICITOS]
perfiles = [
    en_el_instante(*explicitos[r], instante)
    for r in R_EXPLICITOS
    for instante in INSTANTES
]
panel = np.repeat(paneles, len(INSTANTES) * NODOS)
instante = np.tile(np.repeat([f"t = {s}" for s in INSTANTES], NODOS), 3)
xs = np.tile(x, len(perfiles))
# Fuera de la escala el valor exacto no cambia el dibujo; la anotación lo da.
numerico = np.clip(np.concatenate([T for _, T in perfiles]), -200.0, 300.0)
exacto = np.concatenate([fourier(t) for t, _ in perfiles])

P.figure(
    P.line(
        x=xs, y=exacto, z=instante, fx=panel, stroke="currentColor", strokeWidth=0.8
    ),
    P.line(x=xs, y=numerico, stroke=instante, fx=panel, marker="dot", clip=True),
    P.text(
        text=[f"máx|T| = {np.abs(explicitos[r][1]).max():.3g}" for r in R_EXPLICITOS],
        fx=paneles,
        frameAnchor="bottom-left",
        dx=6,
        dy=-6,
        stroke="var(--plot-background)",
        strokeWidth=6,
        fill="currentColor",
    ),
    x={"label": "x"},
    y={"label": "T(x, t)", "domain": [-20, 120]},
    fx={"label": None, "domain": paneles},
    color={"legend": True},
    grid=True,
    width=1000,
    height=320,
)
```

```python hidden
t_inestable, T_inestable = explicitos[0.6]
t_sale = t_inestable[np.argmax(np.abs(T_inestable).max(axis=1) > 120)]
md(
    f"""
    Con $r=0.4$ el perfil sigue a la solución exacta. Con $r=0.5$ también, pero
    en el límite de estabilidad: el modo más oscilante no decae y conserva el
    ruido que el salto inicial en el borde le entrega. Con $r=0.6$ ese modo se
    multiplica por $1-4r={1 - 4 * 0.6:.1f}$ en cada paso, y el perfil que se ve
    es sólo la oscilación de nodo a nodo, muchos órdenes de magnitud mayor que
    la temperatura física.

    La animación sigue a $r=0.4$ y $r=0.6$ cada $0.03$ de tiempo. La oscilación
    de $r=0.6$ aparece junto al borde caliente, donde está el salto inicial, se
    propaga hacia la izquierda y en $t={t_sale:.2f}$ sale de la gráfica; desde
    ahí la etiqueta del cuadro sigue su crecimiento mientras $r=0.4$ sigue a la
    solución de Fourier.
    """
)
```

```python hidden
tiempos = np.arange(0.0, T_FINAL + 1e-9, 0.03)
estable = np.array([en_el_instante(*explicitos[0.4], s)[1] for s in tiempos])
inestable = np.array([en_el_instante(*explicitos[0.6], s)[1] for s in tiempos])

P.figure(
    P.line(
        x=x,
        y=np.array([fourier(s) for s in tiempos]),
        series="Fourier",
        strokeWidth=7,
        strokeOpacity=0.35,
    ),
    P.line(x=x, y=estable, series="r = 0.4", marker="dot"),
    P.line(
        x=x,
        y=np.clip(inestable, -200.0, 300.0),
        series="r = 0.6",
        marker="dot",
        clip=True,
    ),
    frames=[
        f"t = {s:.2f}, máx|T| con r = 0.6: {np.abs(T).max():.3g}"
        for s, T in zip(tiempos, inestable, strict=True)
    ],
    fps=8,
    digits=4,
    title="Explícito estable e inestable frente a la solución de Fourier",
    x={"label": "x"},
    y={"label": "T(x, t)", "domain": [-20, 120]},
    grid=True,
)
```

## Crank–Nicolson y el error en el tiempo

Repetimos la integración con Crank–Nicolson y los mismos $\Delta t$, y medimos
$\max_i|T_i^n-T(x_i,t_n)|$ en cada paso para los dos esquemas.

```python
cn = {r: crank_nicolson(r, T_FINAL) for r in (0.6, 5.0, 20.0)}


def error_en_el_tiempo(t, T):
    return np.array([np.abs(T[k] - fourier(t[k])).max() for k in range(len(t))])
```

```python hidden
corridas = [
    *[("explícito", r, *explicitos[r]) for r in R_EXPLICITOS],
    *[("Crank–Nicolson", r, *cn[r]) for r in cn],
]
errores = [error_en_el_tiempo(t, T) for _, _, t, T in corridas]

P.figure(
    *[
        P.line(
            x=t[1:],
            y=error[1:],
            series=f"{nombre}, r = {r}",
            **({"strokeDasharray": "6 4"} if nombre == "Crank–Nicolson" else {}),
        )
        for (nombre, r, t, _), error in zip(corridas, errores, strict=True)
        if r != 20.0
    ],
    title="Error frente a la solución de Fourier",
    x={"label": "t"},
    y={"label": "máxᵢ |Tᵢⁿ − T(xᵢ, tₙ)|", "type": "log"},
    color={"legend": True},
    grid=True,
)
```

```python hidden
filas = [
    f"| {nombre} | {r} | {r * dx**2 / ALFA:.4f} | {len(t) - 1} "
    f"| {T.min():.3g} | {T.max():.3g} | {error[-1]:.2g} | {error[1:].max():.2g} |"
    for (nombre, r, t, T), error in zip(corridas, errores, strict=True)
]
md(
    "\n".join(
        [
            f"Resultados hasta $t={T_FINAL}$ (la solución física está entre 0 y 100). "
            f"El error final es el de $t={T_FINAL}$; el error máximo es el mayor "
            "en todo el tiempo y ocurre en los primeros pasos: la "
            "condición inicial es discontinua en la esquina $(x=L,\\,t=0)$ y "
            "ningún esquema la representa con pocos pasos.",
            "",
            r"| esquema | $r$ | $\Delta t$ | pasos | $\min T$ | $\max T$ | error final | error máximo |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

```python hidden
INSTANTE = 0.75
_, estable = en_el_instante(*explicitos[0.4], INSTANTE)

P.figure(
    P.line(x=x, y=fourier(INSTANTE), series="Fourier", strokeWidth=1.5),
    *[
        P.line(
            x=x,
            y=en_el_instante(*cn[r], INSTANTE)[1],
            series=f"Crank–Nicolson, r = {r}",
            marker="dot",
        )
        for r in (0.6, 5.0)
    ],
    P.line(
        x=x,
        y=estable,
        series="explícito, r = 0.4",
        marker="circle-stroke",
        strokeDasharray="6 4",
    ),
    title=f"Perfiles en t = {INSTANTE}",
    x={"label": "x"},
    y={"label": "T(x, t)"},
    color={"legend": True},
    grid=True,
)
```

```python hidden
error_final = {r: error_en_el_tiempo(*cn[r])[-1] for r in cn}
md(
    f"""
    Crank–Nicolson no se desestabiliza para ningún $r$. Con $r=0.6$ su error en
    $t=1.5$ es {error_final[0.6]:.2g}, el menor de la tabla. Con $r=5$ el paso
    es {5.0 / 0.6:.1f} veces mayor y el error no crece sin cota. Pero la
    condición inicial es discontinua en $x=L$, y los modos de alta frecuencia
    casi no se amortiguan cuando $r$ es grande: con $r=5$ y $r=20$ aparecen
    valores de hasta {cn[5.0][1].max():.0f} y {cn[20.0][1].max():.0f}, por
    encima de $T_b$, que la solución física nunca alcanza. Para pasos grandes
    conviene un esquema completamente implícito, o arrancar Crank–Nicolson con
    unos pasos pequeños.
    """
)
```
