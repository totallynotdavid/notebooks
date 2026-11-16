```python hidden
import numpy as np
from quire import md
from quire import plot as P
```

# Péndulo doble

Dos masas $m_1, m_2$ cuelgan de varillas rígidas de longitud $\ell_1, \ell_2$.
Los ángulos $(\theta_1,\theta_2)$ medidos desde la vertical y sus velocidades
$(\omega_1,\omega_2)$ forman el estado
$y=(\theta_1,\omega_1,\theta_2,\omega_2)$. Con $\delta=\theta_1-\theta_2$, las
ecuaciones de Lagrange dan

$$
\dot\omega_1 =
\frac{-g(2m_1+m_2)\sin\theta_1 - m_2 g\sin(\theta_1-2\theta_2)
- 2\sin\delta\,m_2\left(\omega_2^2\ell_2+\omega_1^2\ell_1\cos\delta\right)}
{\ell_1\left(2m_1+m_2-m_2\cos 2\delta\right)},
$$

$$
\dot\omega_2 =
\frac{2\sin\delta\left(\omega_1^2\ell_1(m_1+m_2)
+ g(m_1+m_2)\cos\theta_1+\omega_2^2\ell_2 m_2\cos\delta\right)}
{\ell_2\left(2m_1+m_2-m_2\cos 2\delta\right)}.
$$

No hay disipación, así que la energía

$$
\begin{aligned}
E ={}& \tfrac12(m_1+m_2)\ell_1^2\omega_1^2 + \tfrac12 m_2\ell_2^2\omega_2^2
+ m_2\ell_1\ell_2\,\omega_1\omega_2\cos\delta \\
&- (m_1+m_2)g\ell_1\cos\theta_1 - m_2 g\ell_2\cos\theta_2
\end{aligned}
$$

es constante. Esa constante es la vara con que medimos a cada integrador.

```python
M1, M2, L1, L2, G = 1.0, 2.0, 1.0, 1.0, 9.81
Y0 = np.array([1.2, 0.0, 0.8, 0.0])  # theta1, omega1, theta2, omega2


def rhs(y):
    theta1, omega1, theta2, omega2 = y
    delta = theta1 - theta2
    den = 2 * M1 + M2 - M2 * np.cos(2 * delta)
    domega1 = (
        -G * (2 * M1 + M2) * np.sin(theta1)
        - M2 * G * np.sin(theta1 - 2 * theta2)
        - 2 * np.sin(delta) * M2 * (omega2**2 * L2 + omega1**2 * L1 * np.cos(delta))
    ) / (L1 * den)
    domega2 = (
        2
        * np.sin(delta)
        * (
            omega1**2 * L1 * (M1 + M2)
            + G * (M1 + M2) * np.cos(theta1)
            + omega2**2 * L2 * M2 * np.cos(delta)
        )
    ) / (L2 * den)
    return np.array([omega1, domega1, omega2, domega2])


def energy(y):
    theta1, omega1, theta2, omega2 = np.asarray(y).T
    kinetic = (
        0.5 * (M1 + M2) * L1**2 * omega1**2
        + 0.5 * M2 * L2**2 * omega2**2
        + M2 * L1 * L2 * omega1 * omega2 * np.cos(theta1 - theta2)
    )
    potential = -(M1 + M2) * G * L1 * np.cos(theta1) - M2 * G * L2 * np.cos(theta2)
    return kinetic + potential
```

## Dos integradores

Euler explícito avanza con la pendiente al inicio del paso:

$$
y_{n+1} = y_n + \Delta t\,f(y_n).
$$

RK4 evalúa la pendiente cuatro veces dentro del paso y las combina:

$$
y_{n+1} = y_n + \tfrac{\Delta t}{6}\left(k_1+2k_2+2k_3+k_4\right),
$$

con $k_1=f(y_n)$, $k_2=f(y_n+\tfrac{\Delta t}{2}k_1)$, $k_3=f(y_n+\tfrac{\Delta
t}{2}k_2)$ y $k_4=f(y_n+\Delta t\,k_3)$. El error global de Euler es $O(\Delta
t)$ y el de RK4 es $O(\Delta t^4)$.

```python
def step_euler(y, dt):
    return y + dt * rhs(y)


def step_rk4(y, dt):
    k1 = rhs(y)
    k2 = rhs(y + 0.5 * dt * k1)
    k3 = rhs(y + 0.5 * dt * k2)
    k4 = rhs(y + dt * k3)
    return y + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)


def integrate(step, y0, dt, nsteps):
    """El estado en los instantes 0, dt, ..., nsteps*dt."""
    y = np.empty((nsteps + 1, 4))
    y[0] = y0
    for i in range(nsteps):
        y[i + 1] = step(y[i], dt)
    return y


def posiciones(y):
    """Posiciones (x1, y1, x2, y2) de las dos masas."""
    x1, y1 = L1 * np.sin(y[..., 0]), -L1 * np.cos(y[..., 0])
    return x1, y1, x1 + L2 * np.sin(y[..., 2]), y1 - L2 * np.cos(y[..., 2])
```

## Trayectoria con RK4

Con $\Delta t=0.01$ s durante 2500 pasos (25 s) RK4 sigue el movimiento.

```python
dt_fino, pasos_fino = 0.01, 2500
tray_rk4 = integrate(step_rk4, Y0, dt_fino, pasos_fino)
t_fino = np.arange(pasos_fino + 1) * dt_fino
x1, y1, x2, y2 = posiciones(tray_rk4)

P.grid(
    P.figure(
        P.line(x=x2, y=y2, series="masa 2", strokeWidth=0.8),
        P.link(
            x1=[0, x1[-1]],
            y1=[0, y1[-1]],
            x2=[x1[-1], x2[-1]],
            y2=[y1[-1], y2[-1]],
            stroke="currentColor",
            strokeWidth=2,
        ),
        P.dot(x=[0, x1[-1], x2[-1]], y=[0, y1[-1], y2[-1]], r=4, fill="currentColor"),
        title="Camino de la masa 2 y configuración final",
        x={"label": "x [m]", "domain": [-2, 2]},
        y={"label": "y [m]", "domain": [-2, 1]},
        aspectRatio=1,
        grid=True,
    ),
    P.figure(
        P.line(x=t_fino, y=tray_rk4[:, 0], series="θ₁(t)"),
        P.line(x=t_fino, y=tray_rk4[:, 2], series="θ₂(t)"),
        title="Evolución angular (RK4)",
        x={"label": "t [s]"},
        y={"label": "ángulo [rad]"},
        color={"legend": True},
        grid=True,
    ),
)
```

## Deriva de la energía

Integramos las mismas condiciones iniciales con tres configuraciones y medimos
$|E(t)-E(0)|$:

- RK4 con $\Delta t=0.01$ s y 2500 pasos.
- RK4 con $\Delta t=0.05$ s y 10 000 pasos (500 s).
- Euler con $\Delta t=0.01$ s y 2500 pasos.

```python
dt_grueso, pasos_grueso = 0.05, 10_000
tray_rk4_grueso = integrate(step_rk4, Y0, dt_grueso, pasos_grueso)
tray_euler = integrate(step_euler, Y0, dt_fino, pasos_fino)
t_grueso = np.arange(pasos_grueso + 1) * dt_grueso

deriva_rk4 = np.abs(energy(tray_rk4) - energy(Y0))
deriva_rk4_grueso = np.abs(energy(tray_rk4_grueso) - energy(Y0))
deriva_euler = np.abs(energy(tray_euler) - energy(Y0))

md(
    rf"""
    | integrador | $\Delta t$ [s] | pasos | $\max\,\lvert E-E_0\rvert$ [J] |
    |---|---:|---:|---:|
    | RK4 | {dt_fino} | {pasos_fino} | {deriva_rk4.max():.1e} |
    | RK4 | {dt_grueso} | {pasos_grueso} | {deriva_rk4_grueso.max():.1f} |
    | Euler | {dt_fino} | {pasos_fino} | {deriva_euler.max():.0f} |
    """
)
```

```python
P.figure(
    P.line(x=t_fino[1:], y=deriva_euler[1:], series="Euler, Δt = 0.01"),
    P.line(x=t_grueso[1:], y=deriva_rk4_grueso[1:], series="RK4, Δt = 0.05"),
    P.line(x=t_fino[1:], y=deriva_rk4[1:], series="RK4, Δt = 0.01"),
    title="Deriva de la energía total",
    x={"label": "t [s]"},
    y={"label": "|E(t) − E(0)| [J]", "type": "log"},
    color={"legend": True},
    grid=True,
)
```

Euler suma energía en cada paso, desde el primero: la deriva ya es de unos 2 J
tras un segundo y supera varias veces $\lvert E_0\rvert$ antes de los 25 s, así
que su trayectoria deja de representar al péndulo. RK4 con el paso fino conserva
$E$ a $10^{-4}$ J. Con un paso cinco veces mayor la deriva llega a varios julios
en 500 s: RK4 no es simpléctico, el error no queda acotado, y el paso debe
elegirse según el tiempo que se quiere simular.

## Exponente de Lyapunov máximo

Una trayectoria de referencia $y(t)$ y otra que empieza a $d_0=10^{-6}$ de
distancia en el espacio de fases evolucionan juntas. Cuando la separación $d(t)$
crece como $d_0e^{\lambda t}$, $\lambda>0$ es el exponente de Lyapunov máximo.
Para que $d$ no sature en el tamaño del espacio de fases, cada $n$ pasos se
acerca la segunda trayectoria a la primera, sobre la misma dirección, hasta la
distancia $d_0$. Skokos (2010, sec. 5) describe este procedimiento de dos
órbitas vecinas como la forma original de calcular el exponente máximo; después
se sustituyó por la evolución de un vector de desviación con las ecuaciones
variacionales, que admite pasos mayores y no obliga a elegir $d_0$. El estimador
es

$$
\lambda(T) = \frac{1}{T}\sum_k \ln\frac{d_k}{d_0},
$$

donde $d_k$ es la separación justo antes de cada renormalización. Comparamos
tres condiciones iniciales en reposo.

```python
D0 = 1e-6


def lyapunov(y0, dt=0.01, tiempo=100.0, cada=10):
    """Estimador de Benettin de lambda_max y su valor acumulado en el tiempo."""
    a = np.array(y0, dtype=float)
    b = a + np.array([D0, 0.0, 0.0, 0.0])
    suma = 0.0
    t_est, lam = [], []
    for i in range(1, round(tiempo / dt) + 1):
        a = step_rk4(a, dt)
        b = step_rk4(b, dt)
        if i % cada == 0:
            d = np.linalg.norm(b - a)
            suma += np.log(d / D0)
            b = a + (b - a) * (D0 / d)
            t_est.append(i * dt)
            lam.append(suma / (i * dt))
    return np.array(t_est), np.array(lam)


def separacion(y0, dt=0.01, tiempo=15.0):
    """Distancia entre dos trayectorias sin renormalizar."""
    a = np.array(y0, dtype=float)
    b = a + np.array([D0, 0.0, 0.0, 0.0])
    t_sep, dist = [0.0], [D0]
    for i in range(1, round(tiempo / dt) + 1):
        a = step_rk4(a, dt)
        b = step_rk4(b, dt)
        t_sep.append(i * dt)
        dist.append(np.linalg.norm(b - a))
    return np.array(t_sep), np.array(dist)


casos = {
    "ángulos pequeños (0.1, 0.1)": np.array([0.1, 0.0, 0.1, 0.0]),
    "moderado (1.2, 0.8)": Y0,
    "grande (2.5, 2.0)": np.array([2.5, 0.0, 2.0, 0.0]),
}
lambdas = {nombre: lyapunov(y0) for nombre, y0 in casos.items()}

md(
    "\n".join(
        [
            r"| $(\theta_1(0),\theta_2(0))$ [rad] | $\lambda_{\max}$ [1/s], $T=100$ s |",
            "|---|---:|",
            *[f"| {nombre} | {lam[-1]:.2f} |" for nombre, (_, lam) in lambdas.items()],
        ]
    )
)
```

```python
t_sep, d_sep = separacion(casos["grande (2.5, 2.0)"])
lam_grande = lambdas["grande (2.5, 2.0)"][1][-1]

P.grid(
    P.figure(
        P.ruleY([0]),
        *[
            P.line(x=t, y=lam, series=nombre, clip=True)
            for nombre, (t, lam) in lambdas.items()
        ],
        title="Convergencia del estimador de Benettin",
        x={"label": "T [s]"},
        y={"label": "λ(T) [1/s]", "domain": [-0.5, 3]},
        color={"legend": True},
        grid=True,
    ),
    P.figure(
        P.line(x=t_sep, y=d_sep, series="d(t) sin renormalizar"),
        P.line(
            x=t_sep,
            y=D0 * np.exp(lam_grande * t_sep),
            series=f"d₀ e^(λt), λ = {lam_grande:.2f}",
            strokeDasharray="6 4",
            clip=True,
        ),
        title="Separación de dos trayectorias a 10⁻⁶",
        x={"label": "t [s]"},
        y={"label": "distancia en el espacio de fases", "type": "log"},
        color={"legend": True},
        grid=True,
    ),
)
```

Para ángulos grandes $\lambda>0$: una diferencia de una millonésima en la
condición inicial alcanza el tamaño del espacio de fases en pocos segundos, y el
tiempo en que se puede predecir la trayectoria crece sólo como
$\ln(1/d_0)/\lambda$. La gráfica de la derecha muestra que la separación sin
renormalizar sigue esa exponencial hasta saturar.

Para ángulos pequeños el movimiento es casi lineal y el estimador cae hacia cero
al crecer $T$. En el caso moderado también decrece con $T$, lo que es
consistente con $\lambda=0$ (movimiento regular), pero un estimador de tiempo
finito no lo demuestra.

## Dos péndulos casi iguales

```python hidden
DESVIO = 1e-3
DT_ANIM, CADA, TIEMPO_ANIM = 0.002, 20, 10.0
y0 = casos["grande (2.5, 2.0)"]
pasos = round(TIEMPO_ANIM / DT_ANIM)
pos_a, pos_b = (
    posiciones(integrate(step_rk4, inicio, DT_ANIM, pasos)[::CADA])
    for inicio in (y0, y0 + np.array([DESVIO, 0.0, 0.0, 0.0]))
)
t_anim = np.arange(len(pos_a[0])) * DT_ANIM * CADA
distancia = np.hypot(pos_a[2] - pos_b[2], pos_a[3] - pos_b[3])
t_diverge = t_anim[np.argmax(distancia > 0.1)]

md(
    rf"""
    La animación suelta dos péndulos desde $(2.5,\ 2.0)$ rad; el segundo empieza
    con $\theta_1$ mayor en {DESVIO:g} rad. Durante los primeros segundos se
    mueven como uno solo. A los {t_diverge:.1f} s la segunda masa de uno ya está
    a más de 10 cm de la del otro, y poco después sus movimientos no se parecen.
    Cada péndulo deja la estela de su segunda masa en los últimos 0.6 s.
    """
)
```

```python
nombres = ["θ₁(0) = 2.5 rad", "θ₁(0) = 2.5 rad + 10⁻³"]
cuadros = len(t_anim)
# La estela son las últimas 16 posiciones; al empezar repite la primera.
atras = np.arange(-16, 1)
indices = np.clip(np.arange(cuadros)[:, None] + atras, 0, None)
estela_x = np.hstack([p[2][indices] for p in (pos_a, pos_b)])
estela_y = np.hstack([p[3][indices] for p in (pos_a, pos_b)])
cero = np.zeros((cuadros, 1))
# Varillas: pivote a masa 1 y masa 1 a masa 2, de cada péndulo.
x1a, y1a, x2a, y2a = (c[:, None] for c in pos_a)
x1b, y1b, x2b, y2b = (c[:, None] for c in pos_b)

P.figure(
    P.line(
        x=estela_x,
        y=estela_y,
        z=np.repeat(nombres, len(atras)),
        stroke=np.repeat(nombres, len(atras)),
        strokeOpacity=0.5,
        tip=False,
    ),
    P.link(
        x1=np.hstack([cero, x1a, cero, x1b]),
        y1=np.hstack([cero, y1a, cero, y1b]),
        x2=np.hstack([x1a, x2a, x1b, x2b]),
        y2=np.hstack([y1a, y2a, y1b, y2b]),
        stroke=np.repeat(nombres, 2),
        strokeWidth=2,
    ),
    P.dot(
        x=np.hstack([x1a, x2a, x1b, x2b]),
        y=np.hstack([y1a, y2a, y1b, y2b]),
        fill=np.repeat(nombres, 2),
        r=6,
    ),
    P.dot(x=[0], y=[0], r=3, fill="currentColor"),
    frames=[f"t = {s:.1f} s" for s in t_anim],
    fps=1 / (DT_ANIM * CADA),
    title="Dos péndulos dobles que empiezan a 10⁻³ rad",
    x={"domain": [-2.2, 2.2], "axis": None},
    y={"domain": [-2.2, 2.2], "axis": None},
    color={"legend": True},
    aspectRatio=1,
    width=560,
)
```

## Referencia

Ch. Skokos, «The Lyapunov characteristic exponents and their computation»
(2010), doi:10.1007/978-3-642-04458-8_2.
