```python hidden
import numpy as np
from quire import md
from quire import plot as P
```

# Dos masas y tres resortes

Dos masas $m_1, m_2$ se mueven en línea recta entre dos paredes. Un resorte
$k_1$ une la pared izquierda con $m_1$, un resorte $k$ une las masas y un
resorte $k_2$ une $m_2$ con la pared derecha. Con $x_1,x_2$ los desplazamientos
desde el equilibrio,

$$
m_1\ddot x_1 = -k_1x_1 + k\,(x_2-x_1),
\qquad
m_2\ddot x_2 = -k_2x_2 - k\,(x_2-x_1),
$$

o en forma matricial $M\ddot{\mathbf x} = -K\mathbf x$ con

$$
M=\begin{pmatrix} m_1 & 0\\ 0 & m_2\end{pmatrix},
\qquad
K=\begin{pmatrix} k_1+k & -k\\ -k & k_2+k\end{pmatrix}.
$$

## Modos normales

Buscamos soluciones $\mathbf x(t)=\mathbf v\cos(\omega t)$. Sustituir da el
problema de valores propios generalizado $K\mathbf v=\omega^2M\mathbf v$. Con
$A=M^{-1/2}KM^{-1/2}$, simétrica, se reduce a $A\mathbf u=\omega^2\mathbf u$ y
`numpy.linalg.eigh` entrega valores propios reales y vectores ortonormales. Los
modos son $\mathbf v_i=M^{-1/2}\mathbf u_i$ y cumplen $\mathbf v_i^{T}M\mathbf
v_j=\delta_{ij}$.

Las coordenadas modales $q_i=\mathbf v_i^{T}M\,\mathbf x$ desacoplan el sistema:
$\ddot q_i=-\omega_i^2q_i$. Cada modo oscila con una sola frecuencia, y
cualquier movimiento es una superposición de ellos.

```python
M1, M2 = 1.0, 2.0
K1 = K2 = KC = 250.0

masas = np.diag([M1, M2])
rigidez = np.array([[K1 + KC, -KC], [-KC, K2 + KC]])

m_inv_sqrt = np.diag(1.0 / np.sqrt(np.diag(masas)))
valores, u = np.linalg.eigh(m_inv_sqrt @ rigidez @ m_inv_sqrt)
omega = np.sqrt(valores)  # rad/s, de menor a mayor
modos = m_inv_sqrt @ u  # columnas v_i con v_i^T M v_j = delta_ij
# Forma de cada modo con amplitud máxima 1 y x_1 >= 0.
formas = modos / abs(modos).max(axis=0) * np.sign(modos[0])
```

```python hidden
md(
    "\n".join(
        [
            rf"$m_1={M1}$ kg, $m_2={M2}$ kg, $k_1=k_2=k=250$ N/m.",
            "",
            r"| modo | $\omega$ [rad/s] | $f$ [Hz] | $x_1$ | $x_2$ |",
            "|---:|---:|---:|---:|---:|",
            *[
                f"| {i + 1} | {omega[i]:.3f} | {omega[i] / (2 * np.pi):.3f} "
                f"| {formas[0, i]:+.3f} | {formas[1, i]:+.3f} |"
                for i in range(2)
            ],
        ]
    )
)
```

```python hidden
md(
    rf"""
    En el modo de menor frecuencia las masas se mueven en fase, con la masa mayor
    desplazándose más. En el de mayor frecuencia se mueven en oposición,
    estirando y comprimiendo el resorte central, y por eso su frecuencia es
    mayor. Los dos vectores son ortogonales respecto de $M$:

    $$
    {M1}\cdot{formas[0, 0]:.3f}\cdot{formas[0, 1]:.3f}
    + {M2}\cdot{formas[1, 0]:.3f}\cdot({formas[1, 1]:.3f}) = 0.
    $$
    """
)
```

## Integración temporal con RK4

Integramos el sistema de cuatro ecuaciones de primer orden $\dot{\mathbf
x}=\mathbf v,\ \dot{\mathbf v}=-M^{-1}K\mathbf x$ con RK4 y paso $h=0.01$ s,
partiendo del reposo con tres condiciones iniciales:

1. $\mathbf x(0)$ igual al modo 1.
2. $\mathbf x(0)$ igual al modo 2.
3. $x_1(0)=1$ m, $x_2(0)=0$: una mezcla de ambos modos.

La solución analítica desde el reposo es $\mathbf x(t)=\sum_i q_i(0)\,\mathbf
v_i\cos\omega_it$, y la usamos para medir el error de RK4.

```python
H = 0.01
PASOS = 2000  # 20 s
aceleracion = -np.linalg.solve(masas, rigidez)


def f(y):
    return np.concatenate([y[2:], aceleracion @ y[:2]])


def rk4(x0, h=H, pasos=PASOS):
    y = np.empty((pasos + 1, 4))
    y[0] = np.concatenate([x0, [0.0, 0.0]])
    for i in range(pasos):
        k1 = f(y[i])
        k2 = f(y[i] + 0.5 * h * k1)
        k3 = f(y[i] + 0.5 * h * k2)
        k4 = f(y[i] + h * k3)
        y[i + 1] = y[i] + h / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
    return y


def analitica(x0, t):
    q0 = modos.T @ masas @ x0
    return (modos * q0) @ np.cos(np.outer(omega, t))


t = np.arange(PASOS + 1) * H
casos = {
    "modo 1": formas[:, 0],
    "modo 2": formas[:, 1],
    "x₁(0) = 1, x₂(0) = 0": np.array([1.0, 0.0]),
}
trayectorias = {nombre: rk4(x0) for nombre, x0 in casos.items()}
errores = {
    nombre: abs(trayectorias[nombre][:, :2].T - analitica(x0, t)).max()
    for nombre, x0 in casos.items()
}
```

```python
inicio = t <= 3

caso = np.repeat(list(trayectorias), inicio.sum())
tiempo = np.tile(t[inicio], len(trayectorias))
x1, x2 = np.concatenate([y[inicio, :2] for y in trayectorias.values()]).T

P.figure(
    P.line(x=tiempo, y=x1, fx=caso, series="x₁(t)"),
    P.line(x=tiempo, y=x2, fx=caso, series="x₂(t)"),
    x={"label": "t [s]"},
    y={"label": "desplazamiento [m]", "domain": [-1, 1]},
    fx={"label": None, "domain": list(trayectorias)},
    color={"legend": True},
    grid=True,
    width=1000,
    height=300,
)
```

La animación muestra los mismos tres casos durante 3 s, a un tercio de la
velocidad real. Los desplazamientos están dibujados a 0.3 de su escala para que
las masas no se crucen.

```python
ESCALA, CADA, DURACION = 0.3, 2, 3.0
filas = np.array([2.0, 1.0, 0.0])
cuadros = np.arange(0, np.searchsorted(t, DURACION) + 1, CADA)

# Un resorte en zigzag: tramos rectos en los extremos y seis vueltas al centro.
VUELTAS = 6
u = np.concatenate([[0.0, 0.15], np.linspace(0.2, 0.8, 2 * VUELTAS), [0.85, 1.0]])
zigzag = np.concatenate([[0, 0], 0.12 * (-1.0) ** np.arange(2 * VUELTAS), [0, 0]])

# Pared, m₁, m₂ y pared en cada fila: (cuadros, 3 filas, 4 puntos).
centros = np.stack(
    [1.0 + ESCALA * y[cuadros, 0:2] + [0, 1] for y in trayectorias.values()], axis=1
)
extremos = np.concatenate(
    [np.zeros((*centros.shape[:2], 1)), centros, np.full((*centros.shape[:2], 1), 3.0)],
    axis=2,
)
# Cada resorte une dos puntos vecinos: (cuadros, 3 filas, 3 resortes, vértices).
izquierda, derecha = extremos[..., :-1, None], extremos[..., 1:, None]
resortes_x = (izquierda + u * (derecha - izquierda)).reshape(len(cuadros), -1)
resortes_y = (np.repeat(filas, 3)[:, None] + zigzag).ravel()
resorte = np.repeat(np.arange(9), len(u))
centros = centros.reshape(len(cuadros), -1)

P.figure(
    P.link(
        x1=[0, 3] * 3,
        x2=[0, 3] * 3,
        y1=np.repeat(filas, 2) - 0.3,
        y2=np.repeat(filas, 2) + 0.3,
        stroke="currentColor",
        strokeWidth=4,
    ),
    P.line(
        x=resortes_x,
        y=resortes_y,
        z=resorte,
        stroke="currentColor",
        strokeOpacity=0.5,
        tip=False,
    ),
    *[
        P.dot(
            x=centros[:, i::2],
            y=filas,
            r=9 * np.sqrt(m),
            symbol="square",
            series=f"m{'₁₂'[i]} = {m:g} kg",
        )
        for i, m in enumerate((M1, M2))
    ],
    P.text(
        x=[-0.08] * 3,
        y=filas,
        text=list(trayectorias),
        textAnchor="end",
        fontSize=12,
    ),
    frames=[f"t = {s:.2f} s" for s in t[cuadros]],
    fps=1 / (3 * CADA * H),
    title="Los tres casos a un tercio de la velocidad real",
    x={"domain": [-1.3, 3.1], "axis": None},
    y={"domain": [-0.5, 2.5], "axis": None},
    color={"legend": True},
    width=640,
    height=360,
)
```

```python hidden
md(
    "\n".join(
        [
            "| condición inicial | error máximo de RK4 frente a la solución analítica [m] |",
            "|---|---:|",
            *[f"| {n} | {e:.1e} |" for n, e in errores.items()],
        ]
    )
)
```

El error de RK4 es un corrimiento de fase que se acumula durante los 20 s y es
mayor en el modo de mayor frecuencia. Si el movimiento empieza en un modo, las
dos masas oscilan con la misma frecuencia y con una relación de amplitudes fija.
En la mezcla, cada masa muestra las dos frecuencias a la vez.

## Los modos en la serie temporal

Proyectar la serie numérica de la mezcla sobre los modos, $q_i(t)=\mathbf
v_i^{T}M\,\mathbf x(t)$, recupera dos cosenos puros. Y el espectro de $x_1(t)$
tiene exactamente dos picos, en las frecuencias de los modos.

```python
mezcla = trayectorias["x₁(0) = 1, x₂(0) = 0"]
q = modos.T @ masas @ mezcla[:, :2].T

ventana = np.hanning(len(t))
espectro = np.abs(np.fft.rfft(mezcla[:, 0] * ventana))
espectro /= espectro.max()
frecuencia = np.fft.rfftfreq(len(t), d=H)
visible = frecuencia <= 8

P.grid(
    P.figure(
        P.line(x=t[inicio], y=q[0, inicio], series="q₁(t)"),
        P.line(x=t[inicio], y=q[1, inicio], series="q₂(t)"),
        title="Coordenadas modales de la mezcla",
        x={"label": "t [s]"},
        y={"label": "coordenada modal [m·√kg]"},
        color={"legend": True},
        grid=True,
    ),
    P.figure(
        P.ruleX(omega / (2 * np.pi), strokeDasharray="4 3", strokeOpacity=0.6),
        P.text(
            x=omega / (2 * np.pi),
            y=[2, 2],
            text=[
                f"f{'₁₂'[i]} = {w / (2 * np.pi):.2f} Hz" for i, w in enumerate(omega)
            ],
            textAnchor="start",
            dx=4,
            dy=8,
        ),
        P.line(
            x=frecuencia[visible], y=espectro[visible], series="|FFT| de x₁", clip=True
        ),
        title="Espectro de x₁(t)",
        x={"label": "f [Hz]", "domain": [0, 8]},
        y={"label": "|FFT| normalizada", "type": "log", "domain": [1e-4, 2]},
        grid=True,
    ),
)
```
