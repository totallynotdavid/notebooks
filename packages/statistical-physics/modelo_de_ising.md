```python hidden
from itertools import pairwise

import numpy as np
from numba import njit
from quire import md
from quire import plot as P
```

# Modelo de Ising 3D

Hamiltoniano sin campo externo, con $J=1$ y $k_B=1$:

$$
H(\sigma) = -J\sum_{\langle i,j \rangle} s_i s_j,
\qquad s_i \in \{-1,+1\}.
$$

Regla de aceptación de Metropolis para un cambio local con $\Delta E$:

$$
P_{\text{aceptar}} = \min\left(1, e^{-\beta \Delta E}\right).
$$

Para cada tamaño $L$ se simula una red cúbica de $N=L^3$ espines con condiciones
de frontera periódicas, a muchas temperaturas, y se estiman, con $m=\sum_i
s_i/N$ y $e=E/N$,

$$
\langle |m| \rangle,\qquad
\langle e \rangle,\qquad
\chi = \beta N\left(\langle m^2\rangle - \langle |m|\rangle^2\right),\qquad
C = \beta^2 N\left(\langle e^2\rangle - \langle e\rangle^2\right),
$$

$$
U_4 = 1 - \frac{\langle m^4\rangle}{3\langle m^2\rangle^2}.
$$

## Metropolis secuencial

Un barrido visita los $N$ sitios una vez, en orden. Al invertir un espín con
suma de vecinos $h$, la energía cambia en $\Delta E=2s\,h$, que solo toma los
valores $0,\pm4,\pm8,\pm12$: los factores de Boltzmann se calculan una vez.

```python
@njit
def simular(L, beta, barridos, semilla):
    """Metropolis desde la red ordenada.

    Devuelve e = E/N y m = M/N después de cada barrido, y la red final.
    """
    np.random.seed(semilla)
    spins = np.ones((L, L, L), dtype=np.int8)
    n_sitios = L * L * L
    # Vecinos con frontera periódica, sin módulo dentro del bucle.
    mas = (np.arange(L) + 1) % L
    menos = (np.arange(L) - 1) % L
    boltzmann = np.exp(-beta * np.array([0.0, 4.0, 8.0, 12.0]))

    energia = -3 * n_sitios
    magnetizacion = n_sitios
    e = np.empty(barridos, dtype=np.float64)
    m = np.empty(barridos, dtype=np.float64)

    for t in range(barridos):
        for i in range(L):
            for j in range(L):
                for k in range(L):
                    s = spins[i, j, k]
                    vecinos = (
                        spins[mas[i], j, k]
                        + spins[menos[i], j, k]
                        + spins[i, mas[j], k]
                        + spins[i, menos[j], k]
                        + spins[i, j, mas[k]]
                        + spins[i, j, menos[k]]
                    )
                    dE = 2 * s * vecinos
                    if dE <= 0 or np.random.random() < boltzmann[dE // 4]:
                        spins[i, j, k] = -s
                        energia += dE
                        magnetizacion -= 2 * s
        e[t] = energia / n_sitios
        m[t] = magnetizacion / n_sitios

    return e, m, spins


@njit
def barrer_temperaturas(L, temperaturas, replicas, barridos, semilla):
    n_t = temperaturas.shape[0]
    e = np.empty((n_t, replicas, barridos), dtype=np.float64)
    m = np.empty((n_t, replicas, barridos), dtype=np.float64)
    for a in range(n_t):
        for r in range(replicas):
            e[a, r], m[a, r], _ = simular(
                L, 1.0 / temperaturas[a], barridos, semilla + 1000 * a + r
            )
    return e, m
```

## Observables y cumulante de Binder

La rejilla de temperaturas es fina alrededor de la temperatura crítica esperada,
$T_c\approx4.51$. Cada réplica parte de la red ordenada y descarta los primeros
barridos como termalización. Las barras de error son la desviación estándar de
la media entre réplicas.

```python
TAMANOS = (4, 6, 8, 10, 12)
REPLICAS = 6
BARRIDOS = 4000
DESCARTE = 800
SEMILLA = 7
TEMPERATURAS = np.round(
    np.concatenate([[3.0, 3.4, 3.8], np.arange(4.1, 4.95, 0.1), [5.3, 5.8]]), 2
)
# Hasenbusch, Phys. Rev. B 82, 174433 (2010).
BETA_HASENBUSCH = 0.22165463
U4_HASENBUSCH = 1.0 - 1.60357 / 3.0


def momentos_por_replica(L):
    """Observables (n_T, réplicas) para el tamaño L, sin la termalización."""
    e, m = barrer_temperaturas(L, TEMPERATURAS, REPLICAS, BARRIDOS, SEMILLA)
    e = e[:, :, DESCARTE:]
    m = m[:, :, DESCARTE:]
    n = L**3
    beta = (1.0 / TEMPERATURAS)[:, None]
    m_abs = np.abs(m).mean(axis=2)
    m2 = (m**2).mean(axis=2)
    m4 = (m**4).mean(axis=2)
    return {
        "|m|": m_abs,
        "e": e.mean(axis=2),
        "chi": beta * n * (m2 - m_abs**2),
        "C": beta**2 * n * e.var(axis=2),
        "U4": 1.0 - m4 / (3.0 * m2**2),
    }


observables = {L: momentos_por_replica(L) for L in TAMANOS}
```

Para $T>T_c$ el cumulante $U_4$ decrece con $L$ y para $T<T_c$ crece, de modo
que las curvas de dos tamaños se cortan cerca de $T_c$. Cada cruce es el cero de
una recta ajustada a $U_4(L_2)-U_4(L_1)$ en $4.2\le T\le 4.8$. La incertidumbre
es un bootstrap sobre las réplicas.

```python
AJUSTE = (4.2, 4.8)


def cruce(u_pequena, u_grande):
    """Cero de la recta que ajusta U4(L grande) - U4(L pequeña) cerca de Tc."""
    ventana = (AJUSTE[0] <= TEMPERATURAS) & (AJUSTE[1] >= TEMPERATURAS)
    pendiente, ordenada = np.polyfit(
        TEMPERATURAS[ventana], (u_grande - u_pequena)[ventana], 1
    )
    return float(-ordenada / pendiente)


rng_bootstrap = np.random.default_rng(0)
cruces = {}
for chico, grande in pairwise(TAMANOS):
    u_chico = observables[chico]["U4"]
    u_grande = observables[grande]["U4"]
    remuestras = [
        cruce(
            u_chico[:, rng_bootstrap.integers(0, REPLICAS, REPLICAS)].mean(axis=1),
            u_grande[:, rng_bootstrap.integers(0, REPLICAS, REPLICAS)].mean(axis=1),
        )
        for _ in range(400)
    ]
    cruces[(chico, grande)] = (
        cruce(u_chico.mean(axis=1), u_grande.mean(axis=1)),
        float(np.std(remuestras)),
    )
```

```python hidden
md(
    "\n".join(
        [
            r"| tamaños | $T_\times$ | $\beta_\times = 1/T_\times$ |",
            "|---|---:|---:|",
            *[
                f"| {a} y {b} | {t:.3f} ± {err:.3f} | {1 / t:.4f} ± {err / t**2:.4f} |"
                for (a, b), (t, err) in cruces.items()
            ],
            "",
            rf"Hasenbusch da $\beta_c = {BETA_HASENBUSCH}(8)$, es decir"
            rf" $T_c = {1 / BETA_HASENBUSCH:.4f}$.",
        ]
    )
)
```

```python hidden
T_C = 1 / BETA_HASENBUSCH


def panel(clave, titulo, ventana=None, referencia=None):
    """Una curva por tamaño con barras de la desviación de la media."""
    cuales = np.ones(len(TEMPERATURAS), bool) if ventana is None else ventana
    marcas = [P.ruleX([T_C], strokeDasharray="4 3", strokeOpacity=0.6)]
    if referencia is not None:
        marcas.append(P.ruleY([referencia], strokeOpacity=0.6))
    for L in TAMANOS:
        datos = observables[L][clave][cuales]
        media = datos.mean(axis=1)
        error = datos.std(axis=1, ddof=1) / np.sqrt(REPLICAS)
        marcas += [
            P.ruleX(
                x=TEMPERATURAS[cuales],
                y1=media - error,
                y2=media + error,
                series=f"L = {L}",
            ),
            P.line(x=TEMPERATURAS[cuales], y=media, marker="dot", series=f"L = {L}"),
        ]
    return P.figure(
        *marcas,
        title=titulo,
        x={"label": "T (J/k_B)"},
        y={"label": None},
        grid=True,
    )


ventana_cruce = (TEMPERATURAS >= 4.0) & (TEMPERATURAS <= 5.0)
P.grid(
    panel("|m|", "magnetización ⟨|m|⟩"),
    panel("e", "energía ⟨e⟩ = ⟨E/N⟩"),
    panel("chi", "susceptibilidad χ"),
    panel("C", "calor específico C"),
    panel("U4", "cumulante de Binder U₄", referencia=U4_HASENBUSCH),
    panel(
        "U4",
        "U₄ entre T = 4 y 5",
        ventana=ventana_cruce,
        referencia=U4_HASENBUSCH,
    ),
)
```

```python hidden
t_min = min(t for t, _ in cruces.values())
t_max = max(t for t, _ in cruces.values())
md(
    rf"""
    La línea vertical es $T_c=1/\beta_c$ de Hasenbusch. La horizontal en los
    paneles de $U_4$ es $U_4^*=1-1.60357/3 = {U4_HASENBUSCH:.4f}$, el valor
    universal del cumulante en $T_c$, que sale de $U_4^*=1.60357(1)$ en la forma
    $\langle m^4\rangle/\langle m^2\rangle^2$ de Hasenbusch.

    - $\langle |m| \rangle$ pasa de $\approx 1$ a $\approx 0$. La transición se
      afila al crecer $L$.
    - $\chi$ y $C$ tienen un máximo cerca de $T_c$ que crece con $L$. En volumen
      finito ninguno diverge.
    - Los cruces de $U_4$ caen entre ${t_min:.2f}$ y ${t_max:.2f}$, entre
      ${T_C - t_max:.2f}$ y ${T_C - t_min:.2f}$ por debajo de $T_c$, y $U_4$ en
      $T_c$ queda por encima de $U_4^*$ para todo $L$ simulado. Es el efecto de
      las correcciones a la escala de tamaño finito: cerca de $T_c$, $U_4$
      difiere de $U_4^*$ en un término $\propto L^{{-\omega}}$. Hasenbusch halla
      $\omega=0.832(6)$ y, para el modelo de Ising de espín 1/2, una amplitud
      negativa para la razón de momentos, que equivale a un $U_4$ por encima de
      $U_4^*$. Con $L\le 12$ y {REPLICAS} réplicas, los cruces de los tamaños
      mayores tienen una incertidumbre estadística más grande.
    """
)
```

## Configuraciones en equilibrio

La animación recorre la temperatura en una red de $L=32$. Cada cuadro es el
plano $z=0$ después de 1500 barridos desde la red ordenada. Por debajo de $T_c$
domina un solo signo, cerca de $T_c$ aparecen dominios de ambos signos de todos
los tamaños, y por encima los espines son casi independientes.

```python
L_VISTA = 32
TEMPERATURAS_VISTA = np.round(np.arange(3.0, 7.01, 0.25), 2)
vistas = [simular(L_VISTA, 1.0 / T, 1500, 11) for T in TEMPERATURAS_VISTA]
planos = np.array([spins[:, :, 0].ravel() for _, _, spins in vistas])
m_vista = [m[-1] for _, m, _ in vistas]
```

```python hidden
x_red, y_red = np.indices((L_VISTA, L_VISTA)).reshape(2, -1)
P.figure(
    P.cell(
        x=x_red,
        y=y_red,
        fill=np.where(planos > 0, "+1", "−1"),
        inset=0,
        tip=False,
    ),
    title=f"Plano z = 0 de una red de {L_VISTA}³ espines",
    frames=[
        f"T = {T:.2f}, m = {m:+.2f}"
        for T, m in zip(TEMPERATURAS_VISTA, m_vista, strict=True)
    ],
    fps=2,
    x={"axis": None, "padding": 0},
    y={"axis": None, "padding": 0},
    width=480,
    color={"domain": ["+1", "−1"], "legend": True},
    aspectRatio=1,
)
```

Con $L\le 12$ las curvas de arriba tienen efectos de tamaño finito marcados, y
la comparación con el $T_c$ del límite termodinámico es cualitativa.
