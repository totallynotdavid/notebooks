```python hidden
import numpy as np
from quire import md
from quire import plot as P
```

# Péndulo simple

Una masa en el extremo de una varilla rígida de longitud $\ell$ obedece

$$
\ddot\theta + \omega_0^2\sin\theta = 0,\qquad \omega_0^2=\frac{g}{\ell},
$$

con energía por unidad de masa y de $\ell^2$

$$
E = \tfrac12\dot\theta^2 + \omega_0^2\,(1-\cos\theta).
$$

Para ángulos pequeños $\sin\theta\approx\theta$ y el período es
$T_0=2\pi/\omega_0$, independiente de la amplitud. Esta página mide cuánto falla
esa aproximación y qué integrador numérico conserva mejor la energía.

## Período exacto

Integrar $E$ entre el ángulo máximo $\theta_0$ y $0$ da el período como una
integral elíptica completa de primera especie:

$$
T = \frac{4}{\omega_0}\,K\!\left(m\right),
\qquad
K(m)=\int_0^{\pi/2}\frac{d\phi}{\sqrt{1-m\sin^2\phi}},
\qquad
m=\sin^2\frac{\theta_0}{2}.
$$

Para $\theta_0\to0$, $K(0)=\pi/2$ y se recupera $T_0$. Calculamos $K$ con la
media aritmético-geométrica,
$K(m)=\pi/\left[2\,\mathrm{AGM}(1,\sqrt{1-m})\right]$, que converge en pocas
iteraciones. Como comprobación independiente, integramos la ecuación no lineal
con RK4 ($\Delta t=10^{-3}$ s) y medimos el período como cuatro veces el tiempo
hasta el primer cruce por $\theta=0$.

```python
G, LARGO = 9.81, 1.0
OMEGA0 = np.sqrt(G / LARGO)
T0 = 2 * np.pi / OMEGA0


def agm(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    for _ in range(40):
        a, b = (a + b) / 2, np.sqrt(a * b)
    return a


def elliptic_k(m):
    return np.pi / (2 * agm(1.0, np.sqrt(1.0 - m)))


def periodo_exacto(theta0):
    return 4 / OMEGA0 * elliptic_k(np.sin(theta0 / 2) ** 2)


def periodo_serie(theta0):
    """Dos primeros términos de la serie en la amplitud."""
    return T0 * (1 + theta0**2 / 16)


def rhs(y):
    return np.array([y[1], -(OMEGA0**2) * np.sin(y[0])])


def paso_rk4(y, dt):
    k1 = rhs(y)
    k2 = rhs(y + 0.5 * dt * k1)
    k3 = rhs(y + 0.5 * dt * k2)
    k4 = rhs(y + dt * k3)
    return y + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)


def paso_verlet(y, dt):
    """Velocity Verlet: la aceleración sólo depende de la posición."""
    theta, omega = y
    a = -(OMEGA0**2) * np.sin(theta)
    theta_nuevo = theta + omega * dt + 0.5 * a * dt**2
    a_nuevo = -(OMEGA0**2) * np.sin(theta_nuevo)
    return np.array([theta_nuevo, omega + 0.5 * (a + a_nuevo) * dt])


def periodo_numerico(theta0, dt=1e-3):
    y, t = np.array([theta0, 0.0]), 0.0
    while True:
        y_nuevo = paso_rk4(y, dt)
        if y_nuevo[0] <= 0.0:
            # Interpolación lineal del cruce dentro del último paso.
            return 4 * (t + dt * y[0] / (y[0] - y_nuevo[0]))
        y, t = y_nuevo, t + dt


def energia(y):
    return 0.5 * y[..., 1] ** 2 + OMEGA0**2 * (1 - np.cos(y[..., 0]))
```

```python hidden
amplitudes_deg = np.array([5, 10, 30, 60, 90, 120, 150, 170])
theta0 = np.radians(amplitudes_deg)
exacto = periodo_exacto(theta0)
numerico = np.array([periodo_numerico(a) for a in theta0])
serie = periodo_serie(theta0)
filas = [
    f"| {d} | {e:.5f} | {n:.5f} | {100 * abs(T0 - e) / e:.2f} | {100 * abs(s - e) / e:.3f} |"
    for d, e, n, s in zip(amplitudes_deg, exacto, numerico, serie, strict=True)
]
md(
    "\n".join(
        [
            rf"$T_0={T0:.5f}$ s para $\ell=1$ m, $g=9.81$ m/s².",
            "",
            r"| $\theta_0$ [°] | $T$ exacto [s] | $T$ RK4 [s] | error de $T_0$ [%] | error de $T_0(1+\theta_0^2/16)$ [%] |",
            "|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

```python
grados = np.linspace(1, 175, 300)
exacto = periodo_exacto(np.radians(grados))
serie = periodo_serie(np.radians(grados))

P.grid(
    P.figure(
        P.ruleY([1], series="pequeñas oscilaciones", strokeDasharray="2 3"),
        P.line(x=grados, y=exacto / T0, series="exacto, K(m)"),
        P.line(x=grados, y=serie / T0, series="1 + θ₀²/16", strokeDasharray="6 4"),
        title="Período en función de la amplitud",
        x={"label": "θ₀ [°]"},
        y={"label": "T/T₀", "domain": [0.95, 3.0]},
        color={"legend": True},
        grid=True,
    ),
    P.figure(
        P.line(x=grados, y=np.abs(T0 - exacto) / exacto, series="T₀"),
        P.line(
            x=grados,
            y=np.abs(serie - exacto) / exacto,
            series="T₀(1 + θ₀²/16)",
            strokeDasharray="6 4",
        ),
        title="Error de las aproximaciones",
        x={"label": "θ₀ [°]"},
        y={"label": "error relativo del período", "type": "log"},
        color={"legend": True},
        grid=True,
    ),
)
```

El error de $T_0$ crece como $\theta_0^2/16$: 0.19 % a 10°, 6.8 % a 60° y 43 % a
150°, donde el período real es 1.76 veces el lineal. El período RK4 coincide con
el exacto en las cifras de la tabla. La corrección $1+\theta_0^2/16$ lo reduce a
0.4 % a 60°, pero a 150° todavía falla en 19 %: la serie en $\theta_0$ converge
mal cerca de $\pi$, y por eso existen aproximaciones analíticas más elaboradas.

La animación suelta tres péndulos a la vez desde 30°, 90° y 150°, integrados con
RK4. En la aproximación lineal oscilarían juntos; el de mayor amplitud se queda
atrás desde la primera oscilación.

```python
amplitudes = np.radians([30, 90, 150])
dt, cada = 1e-3, 50  # un cuadro cada 0.05 s
cuadros = round(2 * periodo_exacto(amplitudes[-1]) / (dt * cada))
# rhs opera por columnas, así que RK4 avanza los tres péndulos a la vez.
y = np.array([amplitudes, np.zeros(3)])
angulos = [y[0].copy()]
for _ in range(cuadros):
    for _ in range(cada):
        y = paso_rk4(y, dt)
    angulos.append(y[0].copy())
angulos = np.array(angulos)  # una fila por cuadro, una columna por péndulo
nombres = [
    f"θ₀ = {round(np.degrees(a))}°, T = {periodo_exacto(a):.2f} s" for a in amplitudes
]
x, y = np.sin(angulos), -np.cos(angulos)

P.figure(
    P.dot(x=[0], y=[0], r=3, fill="currentColor"),
    P.link(x1=np.zeros(3), y1=np.zeros(3), x2=x, y2=y, stroke=nombres, strokeWidth=2),
    P.dot(x=x, y=y, r=8, fill=nombres),
    frames=[f"t = {t:.2f} s" for t in dt * cada * np.arange(len(angulos))],
    title=f"Tres amplitudes; en la aproximación lineal T₀ = {T0:.2f} s",
    x={"domain": [-1.2, 1.2], "axis": None},
    y={"domain": [-1.2, 1.2], "axis": None},
    color={"legend": True},
    aspectRatio=1,
    width=560,
)
```

## Deriva de la energía: velocity Verlet y RK4

El péndulo no tiene disipación, así que $E$ debe ser constante. Comparamos dos
integradores con $\theta_0=2$ rad, $\dot\theta_0=0$ y $\Delta t=0.1$ s durante
2000 s (unas 700 oscilaciones):

- Velocity Verlet, de segundo orden y simpléctico: una evaluación de la fuerza
  por paso. Conserva exactamente una energía vecina a $E$, así que el error
  oscila y queda acotado.
- RK4, de cuarto orden: cuatro evaluaciones por paso. Es más preciso en pocos
  períodos, pero no es simpléctico y su error se acumula.

```python
DURACION = 2000.0
DT = 0.1
PASOS = round(DURACION / DT)
THETA_INICIAL = 2.0


def error_energia(paso, dt):
    pasos = round(DURACION / dt)
    y = np.empty((pasos + 1, 2))
    y[0] = (THETA_INICIAL, 0.0)
    for i in range(pasos):
        y[i + 1] = paso(y[i], dt)
    e0 = energia(y[0])
    return (energia(y) - e0) / e0


t_energia = np.arange(PASOS + 1) * DT
error_rk4 = error_energia(paso_rk4, DT)
error_verlet = error_energia(paso_verlet, DT)
```

El error de Verlet oscila más rápido de lo que la página puede mostrar punto a
punto, así que la figura lo dibuja como la franja entre su mínimo y su máximo en
cada intervalo de 2 s. En la escala logarítmica, mueve $\Delta t$: al dividirlo
entre dos, el error de Verlet baja unas 4 veces y el de RK4 unas 30.

```python
TRAMOS = 1000  # intervalos de 2 s
pasos_dt = [0.025, 0.05, 0.1, 0.2]
t_fin = np.arange(1, TRAMOS + 1) * DURACION / TRAMOS
t_medio = t_fin - DURACION / TRAMOS / 2


def tramos(error):
    """Error sin el instante inicial, una fila por intervalo de 2 s."""
    return error[1:].reshape(TRAMOS, -1)


verlet = [tramos(error_energia(paso_verlet, dt)) for dt in pasos_dt]
rk4 = [tramos(error_energia(paso_rk4, dt)) for dt in pasos_dt]

P.grid(
    P.figure(
        P.areaY(
            x=t_medio,
            y1=tramos(error_verlet).min(axis=1),
            y2=tramos(error_verlet).max(axis=1),
            series="velocity Verlet",
            fillOpacity=0.6,
        ),
        P.line(x=t_fin, y=tramos(error_rk4)[:, -1], series="RK4"),
        title=f"Error relativo de la energía, Δt = {DT} s",
        x={"label": "t [s]"},
        y={"label": "(E − E₀)/E₀"},
        color={"legend": True},
        grid=True,
    ),
    P.figure(
        P.line(
            x=t_medio,
            y=np.array([np.abs(t).max(axis=1) for t in verlet]),
            series="velocity Verlet",
        ),
        P.line(x=t_fin, y=np.array([np.abs(t[:, -1]) for t in rk4]), series="RK4"),
        frames=[f"Δt = {dt} s" for dt in pasos_dt],
        parameter="Δt",
        start=pasos_dt.index(DT),
        title="Escala logarítmica: máximo de |E − E₀|/E₀ en cada tramo",
        x={"label": "t [s]", "type": "log"},
        y={"label": "|E − E₀|/E₀", "type": "log"},
        color={"legend": True},
        grid=True,
    ),
)
```

```python hidden
inicio = t_energia <= 50.0
md(
    "\n".join(
        [
            rf"$\Delta t={DT}$ s, {PASOS} pasos.",
            "",
            r"| integrador | $\max\lvert E-E_0\rvert/E_0$ hasta 50 s | $\max\lvert E-E_0\rvert/E_0$ hasta 2000 s |",
            "|---|---:|---:|",
            f"| RK4 | {np.abs(error_rk4[inicio]).max():.1e} | {np.abs(error_rk4).max():.1e} |",
            f"| velocity Verlet | {np.abs(error_verlet[inicio]).max():.1e} | {np.abs(error_verlet).max():.1e} |",
        ]
    )
)
```

```python hidden
cruce = t_energia[np.argmax(np.abs(error_rk4) > np.abs(error_verlet).max())]
md(
    rf"""
    El error de Verlet oscila y no sobrepasa {np.abs(error_verlet).max():.1%}.
    El de RK4 es mucho menor al principio, pero crece en una sola dirección
    (RK4 disipa energía en este problema) y supera la cota de Verlet a los
    {cruce:.0f} s. Para simular muchos períodos con un paso grueso conviene un
    integrador simpléctico; para un intervalo corto y exacto, RK4. RK4 cuesta
    cuatro evaluaciones de la fuerza por paso y Verlet una.
    """
)
```
