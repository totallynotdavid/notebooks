```python hidden
import numpy as np
from quire import md, parameter
from quire import plot as P
```

# Atractor de Lorenz

Lorenz (_J. Atmos. Sci._ 20, 130, 1963) redujo la convección en una capa de
fluido calentada desde abajo a tres variables: $x$ es proporcional a la
intensidad de la convección, $y$ a la diferencia de temperatura entre la
corriente que sube y la que baja, y $z$ a cuánto se aparta de una recta el
perfil vertical de temperatura.

$$
\begin{aligned}
\dot x &= \sigma (y - x),\\
\dot y &= x(\rho - z) - y,\\
\dot z &= xy - \beta z.
\end{aligned}
$$

$\sigma$ es el número de Prandtl, $\rho$ es el número de Rayleigh dividido entre
el de inicio de la convección, y $\beta = 4/(1 + a^2)$ depende de la razón de
aspecto $a$ de las celdas. Tomamos los valores de Lorenz: $\sigma = 10$ y
$\beta = 8/3$, y $\rho = 28$, algo por encima de $\rho_H = 470/19 \approx
24.74$, donde la convección estacionaria deja de ser estable (la última sección
deduce ese valor). Integramos con RK4, definido en el
[péndulo simple](../simple-pendulum/), con el paso adimensional de Lorenz,
$\Delta t = 0.01$.

La página construye el atractor, comprueba el orden del integrador, mide cuán
rápido se separan dos trayectorias vecinas, reduce el flujo a un mapa de una
variable y sigue cómo cambia el movimiento con $\rho$.

```python
SIGMA, RHO, BETA = 10.0, 28.0, 8.0 / 3.0
PARAMETROS = (SIGMA, RHO, BETA)
DT = 0.01


def lorenz(s, sigma, rho, beta):
    """Evalúa el campo para uno o varios estados (columnas de s)."""
    x, y, z = s
    return np.array([sigma * (y - x), x * (rho - z) - y, x * y - beta * z])


def rk4(s, dt, p):
    k1 = lorenz(s, *p)
    k2 = lorenz(s + dt / 2 * k1, *p)
    k3 = lorenz(s + dt / 2 * k2, *p)
    k4 = lorenz(s + dt * k3, *p)
    return s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


def integrar(s0, dt, pasos, p):
    """Devuelve todos los estados, incluido el inicial."""
    s = np.asarray(s0, dtype=np.float64)
    historia = np.empty((pasos + 1, *s.shape))
    historia[0] = s
    for i in range(pasos):
        s = rk4(s, dt, p)
        historia[i + 1] = s
    return historia
```

## El atractor

La divergencia del campo es $-(\sigma + \beta + 1) = -41/3$ en todo punto, así
que cualquier volumen del espacio de fases se contrae como $e^{-41t/3}$ y las
trayectorias acaban en un conjunto de volumen nulo, el atractor. Para $\rho > 1$
el origen, que es el fluido en reposo, es inestable, y aparecen dos puntos
fijos, uno por sentido de giro de la convección:

$$
C_\pm = \left(\pm\sqrt{\beta(\rho-1)},\ \pm\sqrt{\beta(\rho-1)},\ \rho-1\right)
= (\pm 6\sqrt{2},\ \pm 6\sqrt{2},\ 27).
$$

Con $\rho > \rho_H$ también son inestables. La trayectoria que sale de $(0.1, 0,
0)$ se aleja en espiral de uno de ellos y pasa al otro. El color marca el
tiempo.

```python hidden
ESTADO_INICIAL = (0.1, 0.0, 0.0)
puntos = integrar(ESTADO_INICIAL, DT, 5000, PARAMETROS)
t_puntos = DT * np.arange(len(puntos))
x, y, z = puntos.T


def proyeccion(h, v, etiqueta_h, etiqueta_v, titulo):
    return P.figure(
        # z=None keeps one line; by default Plot splits a line by its stroke.
        P.line(x=h, y=v, stroke=t_puntos, z=None, strokeWidth=0.7, tip=False),
        title=titulo,
        x={"label": etiqueta_h},
        y={"label": etiqueta_v},
        color={"scheme": "viridis", "label": "t", "legend": True},
        aspectRatio=1,
        grid=True,
    )


P.grid(
    proyeccion(x, z, "x", "z", "Plano x–z: las dos alas"),
    proyeccion(x, y, "x", "y", "Plano x–y"),
)
```

```python hidden
# Una vuelta termina en un máximo de z; el signo de x dice alrededor de qué
# punto fijo fue.
picos = np.flatnonzero((z[1:-1] > z[:-2]) & (z[1:-1] >= z[2:])) + 1
lados = np.sign(x[picos])
cambios = np.flatnonzero(np.diff(lados)) + 1
vueltas = np.diff(np.concatenate([[0], cambios, [lados.size]]))[1:-1]
lista = ", ".join(str(v) for v in vueltas[1:13])
z_picos = z[picos][:-1]
cambia = lados[1:] != lados[:-1]
# La primera racha es la espiral que sale de C₊; el umbral se mide después.
despues = picos[:-1] > picos[cambios[0]]
cambio_min = z_picos[cambia & despues].min()
sigue_max = z_picos[~cambia & despues].max()
md(f"""
Cada vuelta termina en un máximo de $z$, y el signo de $x$ en ese máximo dice
alrededor de cuál punto fijo fue. La primera racha, la espiral que se aleja de
$C_+$, dura {vueltas[0]} vueltas; las siguientes duran {lista}. Lorenz notó que
la trayectoria cambia de lado justo después de un máximo de $z$ mayor que un
umbral, cerca de 38.5 en estas unidades. Aquí todo cambio sigue a un máximo de
al menos {cambio_min:.2f}, y todo máximo sin cambio queda por debajo de
{sigue_max:.2f}.
""")
```

## Orden del integrador

RK4 tiene error global $O(\Delta t^4)$: en el régimen asintótico, al reducir el
paso a la mitad el error en $t = 4$ cae $2^4 = 16$ veces. Comparamos con una
solución de referencia de paso $0.0005$.

```python
def estado_final(dt, t=4.0):
    return integrar(ESTADO_INICIAL, dt, round(t / dt), PARAMETROS)[-1]


referencia = estado_final(0.0005)
pasos_orden = [0.02, 0.01, 0.005, 0.0025]
errores = [np.linalg.norm(estado_final(dt) - referencia) for dt in pasos_orden]
cocientes = [""] + [f"{a / b:.1f}" for a, b in zip(errores, errores[1:])]
filas = "\n".join(
    f"| {dt} | {e:.3e} | {c} |" for dt, e, c in zip(pasos_orden, errores, cocientes)
)
md(f"""
| Δt | error en t = 4 | cociente con el paso anterior |
| ---: | ---: | ---: |
{filas}
""")
```

```python hidden
md(f"""
Los primeros cocientes, {cocientes[1]} y {cocientes[2]}, muestran que con pasos
grandes el error aún no está en el régimen asintótico. El último, {cocientes[3]},
ya está cerca de 16.
""")
```

## Mayor exponente de Lyapunov

El método es el del [péndulo doble](../double-pendulum/): dos trayectorias que
empiezan a una distancia $d_0$ se separan como $d(t) \approx d_0\,e^{\lambda_1
t}$ mientras $d$ es pequeña, y como en el atractor $d$ satura en su tamaño, cada
intervalo $\tau$ se mide la separación $d_k$ y se devuelve la segunda
trayectoria a distancia $d_0$ de la primera, en la misma dirección. Con $N$
intervalos,

$$
\lambda_1 \approx \frac{1}{N\tau}\sum_{k=1}^{N} \ln\frac{d_k}{d_0}.
$$

Partimos de 32 puntos del atractor (cada condición inicial evoluciona antes 30
unidades de tiempo para llegar a él) con $d_0 = 10^{-8}$, $\tau = 0.5$ y $N =
400$ (200 unidades de tiempo).

```python
D0 = 1e-8
TAU = 0.5
BLOQUES = 400

rng = np.random.default_rng(0)
semillas = rng.uniform([-15.0, -20.0, 5.0], [15.0, 20.0, 40.0], size=(32, 3)).T
en_atractor = integrar(semillas, DT, 3000, PARAMETROS)[-1]


def lyapunov(a, p, dt=DT):
    """Devuelve el exponente acumulado de cada par tras cada bloque."""
    direccion = rng.normal(size=a.shape)
    b = a + D0 * direccion / np.linalg.norm(direccion, axis=0)
    suma = np.zeros(a.shape[1])
    acumulado = np.empty((BLOQUES, a.shape[1]))
    for k in range(BLOQUES):
        for _ in range(round(TAU / dt)):
            a = rk4(a, dt, p)
            b = rk4(b, dt, p)
        diferencia = b - a
        d = np.linalg.norm(diferencia, axis=0)
        suma += np.log(d / D0)
        b = a + diferencia * (D0 / d)
        acumulado[k] = suma / ((k + 1) * TAU)
    return acumulado


acumulado = lyapunov(en_atractor, PARAMETROS)
lambdas = acumulado[-1]
lambda_1 = lambdas.mean()
```

```python hidden
t_bloques = TAU * np.arange(1, BLOQUES + 1)
pares = np.tile(np.arange(acumulado.shape[1]), BLOQUES)
P.figure(
    P.line(
        x=np.repeat(t_bloques, acumulado.shape[1]),
        y=acumulado.ravel(),
        z=pares,
        stroke="currentColor",
        strokeOpacity=0.12,
        strokeWidth=0.7,
        clip=True,
        tip=False,
    ),
    P.ruleY([0]),
    P.line(x=t_bloques, y=acumulado.mean(axis=1), series="promedio", strokeWidth=2),
    title="Mayor exponente de Lyapunov (32 pares de trayectorias)",
    x={"label": "t"},
    y={"label": "λ₁ acumulado", "domain": [-0.5, 2.5]},
    grid=True,
)
```

```python hidden
error = lambdas.std(ddof=1) / np.sqrt(lambdas.size)
md(f"""
$\\lambda_1 = {lambda_1:.3f} \\pm {error:.3f}$ (error estándar de los 32 pares;
la desviación entre pares es {lambdas.std(ddof=1):.3f}). Un valor positivo indica
dependencia sensible de las condiciones iniciales: una diferencia se multiplica
por $e$ cada {1 / lambda_1:.1f} unidades de tiempo.
""")
```

### Separación sin renormalizar

Un par de trayectorias sin renormalizar muestra las dos fases: un crecimiento
exponencial y la saturación en el tamaño del atractor. La recta es $d_0
e^{\lambda_1 t}$ con el $\lambda_1$ de arriba. La figura repite el par con
distancias iniciales $d_0$ de $10^{-2}$ a $10^{-12}$ a lo largo de $x$.

```python hidden
SUPERINDICE = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
exponentes = np.arange(2, 13)
a0 = en_atractor[:, 0]
# Columna 0: la trayectoria de referencia; las demás, desplazadas d₀ en x.
inicios = np.tile(a0[:, None], (1, exponentes.size + 1))
inicios[0, 1:] += 10.0**-exponentes
pares = integrar(inicios, DT, 4000, PARAMETROS)
separaciones = np.linalg.norm(pares[:, :, 1:] - pares[:, :, :1], axis=1).T
t_par = DT * np.arange(pares.shape[0])
t_10 = t_par[np.argmax(separaciones > 10, axis=1)]
par = pares[:, :, [0, np.flatnonzero(exponentes == 8)[0] + 1]]
distancia = separaciones[exponentes == 8][0]

d0 = parameter(
    "d₀",
    ["10" + str(-k).translate(SUPERINDICE) for k in exponentes],
    value="10⁻⁸",
)
md(f"""
Arrastra la distancia inicial: con $d_0 =$ {d0} la distancia supera 10 en
$t \\approx$ {d0.each(t_10):.1f}, y $\\ln(10/d_0)/\\lambda_1$ predice
{d0.each(np.log(10 / 10.0**-exponentes) / lambda_1):.1f}. Cada factor 10 en
$d_0$ suma en promedio {np.log(10) / lambda_1:.1f} unidades de tiempo, pero los
tiempos medidos avanzan a saltos alrededor de esa recta, porque $d(t)$ crece
más rápido en unos tramos del atractor que en otros.
""")
```

```python hidden
muestra = slice(None, None, 5)
recta = np.array([0.0, 40.0])
P.figure(
    P.line(
        x=np.tile(t_par[muestra], exponentes.size),
        y=separaciones[:, muestra].ravel(),
        z=np.repeat(exponentes, t_par[muestra].size),
        stroke="currentColor",
        strokeOpacity=0.2,
        tip=False,
    ),
    P.line(x=t_par[muestra], y=separaciones[:, muestra], series="d(t)"),
    P.line(
        x=recta,
        y=10.0 ** -exponentes[:, None] * np.exp(lambda_1 * recta),
        series="d₀ e^(λ₁ t)",
        strokeDasharray="6 4",
        clip=True,
    ),
    frames=d0,
    title="Separación de dos trayectorias según la distancia inicial d₀",
    x={"label": "t"},
    y={"label": "d(t)", "type": "log", "domain": [1e-13, 1e3]},
    grid=True,
)
```

```python hidden
t_visible = t_par[np.argmax(distancia > 10)]
md(f"""
La animación sigue el par con $d_0 = 10^{{-8}}$ en el tramo en que la separación
se hace visible: las dos trayectorias en el plano $x$–$z$, sobre el atractor en
gris. Van superpuestas
mientras $d$ es pequeña frente al atractor; en $t \\approx {t_visible:.1f}$ la
distancia supera 10 y cada una sigue su propio camino.
""")
```

```python
INICIO, FIN, CADA = 14.0, 24.0, 4
cuadros = np.arange(round(INICIO / DT), round(FIN / DT) + 1, CADA)
# La estela cubre las últimas 0.6 unidades de tiempo, un punto cada 2 pasos.
estela = cuadros[:, None] + 2 * np.arange(-30, 1)
fondo = par[:2001, :, 0]
nombres = ["trayectoria 1", "trayectoria 2"]

P.figure(
    P.line(
        x=fondo[:, 0],
        y=fondo[:, 2],
        stroke="currentColor",
        strokeOpacity=0.15,
        tip=False,
    ),
    *[
        P.line(
            x=par[estela, 0, j],
            y=par[estela, 2, j],
            series=nombres[j],
            strokeWidth=2,
            tip=False,
        )
        for j in range(2)
    ],
    P.dot(
        x=par[cuadros][:, 0, :],
        y=par[cuadros][:, 2, :],
        fill=np.tile(nombres, (cuadros.size, 1)),
        r=5,
        tip=False,
    ),
    frames=[f"t = {t_par[k]:.1f}, d = {distancia[k]:.1e}" for k in cuadros],
    fps=16,
    x={"label": "x", "domain": [-20, 20]},
    y={"label": "z", "domain": [3, 50]},
    aspectRatio=1,
    width=560,
    digits=3,
)
```

## Mapa de Lorenz

Si $z_n$ es el $n$-ésimo máximo local de $z(t)$, los puntos $(z_n, z_{n+1})$
caen casi sobre una curva con un solo pico (Lorenz 1963, fig. 4): cada máximo
determina el siguiente, y el flujo tridimensional se reduce, para esta sucesión,
a una función de una variable. Lorenz la idealizó como el mapa tienda $M_{n+1} =
2M_n$ si $M_n < 1/2$ y $M_{n+1} = 2 - 2M_n$ si $M_n > 1/2$, cuyas dos ramas
tienen pendiente de valor absoluto 2. Con esa pendiente, una diferencia entre
dos sucesiones se duplica en cada máximo. Cada máximo se refina con la parábola
que pasa por los tres puntos que lo rodean.

```python
historia_z = integrar(en_atractor, DT, 10_000, PARAMETROS)[:, 2, :]
z0, z1, z2 = historia_z[:-2], historia_z[1:-1], historia_z[2:]
es_maximo = (z1 > z0) & (z1 >= z2)
vertice = z1 + (z2 - z0) ** 2 / (8 * (2 * z1 - z0 - z2))

zn, zn1 = [], []
for j in range(historia_z.shape[1]):
    maximos = vertice[es_maximo[:, j], j]
    zn.append(maximos[:-1])
    zn1.append(maximos[1:])
zn = np.concatenate(zn)
zn1 = np.concatenate(zn1)
```

```python hidden
rango = [zn.min(), zn.max()]
P.figure(
    P.dot(x=zn, y=zn1, r=1.2, series="pares de máximos"),
    P.line(x=rango, y=rango, series="zₙ₊₁ = zₙ", strokeDasharray="6 4", tip=False),
    title="Mapa de Lorenz",
    x={"label": "zₙ"},
    y={"label": "zₙ₊₁"},
    aspectRatio=1,
    width=560,
    grid=True,
)
```

```python hidden
# El punto fijo de la rama derecha se interpola donde z_{n+1} - z_n cambia de
# signo; la pendiente se ajusta con los puntos a menos de 0.5 de él.
critico = zn[np.argmax(zn1)]
derecha = zn > critico
orden = np.argsort(zn[derecha])
xs, ys = zn[derecha][orden], zn1[derecha][orden]
i = np.nonzero(np.diff(np.sign(ys - xs)))[0][0]
fijo = xs[i] - (ys[i] - xs[i]) * (xs[i + 1] - xs[i]) / (
    (ys[i + 1] - xs[i + 1]) - (ys[i] - xs[i])
)
cerca = np.abs(xs - fijo) < 0.5
pendiente = np.polyfit(xs[cerca], ys[cerca], 1)[0]
md(f"""
Son {zn.size} pares de máximos de los 32 puntos de partida. La curva tiene un
pico agudo en $z_n \\approx {critico:.1f}$, el umbral de cambio de lado de la
sección anterior, y cruza la diagonal en $z^* \\approx {fijo:.1f}$, donde su
pendiente ajustada es {pendiente:.2f}, cerca del $-2$ de la rama derecha del
mapa tienda. Como $|f'(z^*)| > 1$, ese punto fijo del
mapa es inestable: dos sucesiones de máximos que empiezan cerca de $z^*$ se
separan en cada paso.
""")
```

## Diagrama de bifurcación en $\rho$

Para cada $\rho$ integramos desde las cercanías del punto fijo
$(\sqrt{\beta(\rho-1)}, \sqrt{\beta(\rho-1)}, \rho - 1)$, descartamos 30
unidades de tiempo y registramos los máximos de $z$ en las 60 siguientes. Un
punto fijo estable aparece como un solo punto, una órbita periódica como pocos
puntos y el caos como una nube. Los puntos fijos $C_\pm$ pierden su estabilidad
cuando dos raíces de su ecuación característica cruzan el eje imaginario (Lorenz
1963, ec. 34), una bifurcación de Hopf, en

$$
\rho_H = \frac{\sigma(\sigma + \beta + 3)}{\sigma - \beta - 1}.
$$

Si $\sigma < \beta + 1$, ningún $\rho$ positivo cumple la condición y $C_\pm$
son estables para todo $\rho > 1$.

```python
rhos = np.linspace(20.0, 230.0, 700)
semilla = np.sqrt(BETA * (rhos - 1))
s = np.array([semilla, semilla, rhos - 1]) + 0.1
p = (SIGMA, rhos, BETA)

for _ in range(3000):
    s = rk4(s, DT, p)
z_bif = np.empty((6000, rhos.size))
for k in range(6000):
    s = rk4(s, DT, p)
    z_bif[k] = s[2]

es_maximo = (z_bif[1:-1] > z_bif[:-2]) & (z_bif[1:-1] >= z_bif[2:])
# Los últimos 40 máximos de cada ρ bastan para dibujar la nube.
ultimos = np.cumsum(es_maximo[::-1], axis=0)[::-1] <= 40
k, j = np.nonzero(es_maximo & ultimos)
rho_maximos = rhos[j]
z_maximos = z_bif[1:-1][k, j]
rho_hopf = SIGMA * (SIGMA + BETA + 3) / (SIGMA - BETA - 1)
```

```python hidden
P.figure(
    P.dot(x=rho_maximos, y=z_maximos, r=0.6, fill="currentColor", tip=False),
    P.ruleX([RHO], series="ρ = 28"),
    P.ruleX([rho_hopf], series=f"Hopf, ρ_H = {rho_hopf:.2f}"),
    title="Diagrama de bifurcación del sistema de Lorenz",
    x={"label": "ρ"},
    y={"label": "máximos de z"},
    digits=3,
)
```
