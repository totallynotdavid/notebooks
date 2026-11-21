```python hidden
import numpy as np
from dinamica_molecular import analisis, lennard_jones, tight_binding
from quire import md
from quire import plot as P
```

# Argón líquido y cúmulos de potasio

La dinámica molecular integra las ecuaciones de Newton de muchos átomos y lee
las propiedades del líquido en sus trayectorias. Esta página repite un punto de
la simulación de argón líquido de Verlet (1967), comprueba que la energía se
conserva, y mide la temperatura, la estructura del líquido y su coeficiente de
difusión. Al final usa el mismo integrador con otro potencial para pequeños
cúmulos de potasio.

Los átomos se mueven con velocity Verlet, definido en el
[péndulo simple](../../dynamics/simple-pendulum/), dentro de una caja cúbica de
lado $L$ repetida periódicamente en las tres direcciones: un átomo que sale por
una cara entra por la opuesta, y no hay paredes. Cada átomo tiene entonces
infinitas copias desplazadas en múltiplos de $L$. La convención de **mínima
imagen** toma, para cada par, solo la copia más cercana: cada componente de la
separación se lleva al intervalo $[-L/2, L/2]$. Como esa regla vale para
cualquier posición, el código nunca devuelve los átomos a la caja, y las
posiciones sin envolver dan directamente el desplazamiento que mide la difusión.

El potencial de pares es

$$
V(r) = 4\varepsilon\left[\left(\frac{\sigma}{r}\right)^{12}
- \left(\frac{\sigma}{r}\right)^{6}\right],
$$

truncado en $r_c = 2.5\,\sigma$ y desplazado para que tanto $V$ como la fuerza
se anulen en $r_c$. Se trabaja en unidades reducidas ($\sigma = \varepsilon =
m = 1$); para el argón, $\sigma = 3.405$ Å y $\varepsilon/k_B = 119.8$ K.

Todo se calcula al construir la página: sin datos externos.

```python
# Punto de la tabla I de Verlet: densidad 0.85 y T ~ 0.78.
DENSIDAD = 0.85
T_OBJETIVO = 0.78
DT = 0.004
PASOS_EQUILIBRADO = 1500
PASOS_PRODUCCION = 4000
CADA = 10

pos0, LADO = lennard_jones.red_fcc(4, DENSIDAD)
N = pos0.shape[0]
vel0 = lennard_jones.velocidades_maxwell(N, T_OBJETIVO, np.random.default_rng(1))

equilibrado = lennard_jones.integrar(
    pos0,
    vel0,
    LADO,
    DT,
    PASOS_EQUILIBRADO,
    t_objetivo=T_OBJETIVO,
    cada=PASOS_EQUILIBRADO,
)
corrida = lennard_jones.integrar(
    equilibrado.pos_final,
    equilibrado.vel_final,
    LADO,
    DT,
    PASOS_PRODUCCION,
    cada=CADA,
)
```

```python hidden
md(
    rf"""
    ## Sistema simulado

    | | |
    |---|---|
    | Partículas | {N} (red fcc de 4³ celdas, fundida) |
    | Densidad $\rho^*$ | {DENSIDAD} |
    | Lado de la caja | {LADO:.3f} $\sigma$ |
    | Paso $\Delta t$ | {DT} |
    | Equilibrado (con reescalado de $T$) | {PASOS_EQUILIBRADO} pasos |
    | Producción (energía constante) | {PASOS_PRODUCCION} pasos |
    """
)
```

## Conservación de la energía

Velocity Verlet es simpléctico. Para un hamiltoniano suave, su error en la
energía total $E = K + U$ queda acotado por $C\,\Delta t^2$ durante tiempos muy
largos, sin deriva sistemática (Hairer, Lubich y Wanner 2003, teorema 5.1). El
potencial truncado tiene fuerza continua pero no derivadas continuas en $r_c$,
así que el teorema no se aplica tal cual, y la corrida lo comprueba. En la
producción no hay termostato, así que $E(t)$ es la prueba de que las fuerzas y
el integrador son coherentes. El truncamiento con fuerza desplazada evita los
saltos de energía cuando un par cruza $r_c$.

```python hidden
cada_5 = slice(None, None, 5)
t_energia = corrida.tiempo[cada_5]
desviacion = (corrida.energia_total - corrida.energia_total[0]) / abs(
    corrida.energia_total[0]
)
P.grid(
    P.figure(
        P.line(x=t_energia, y=(corrida.energia_cinetica / N)[cada_5], series="K/N"),
        P.line(x=t_energia, y=(corrida.energia_potencial / N)[cada_5], series="U/N"),
        P.line(x=t_energia, y=(corrida.energia_total / N)[cada_5], series="E/N"),
        title="Energía por partícula (ε)",
        x={"label": "tiempo t"},
        y={"label": None},
        grid=True,
    ),
    P.figure(
        P.ruleY([0], strokeOpacity=0.4),
        P.line(x=t_energia, y=desviacion[cada_5], strokeWidth=1),
        title="Deriva relativa (E(t) − E(0)) / |E(0)|",
        x={"label": "tiempo t"},
        y={"label": None, "tickFormat": ".0e"},
        grid=True,
    ),
)
```

```python hidden
desviacion_max = np.max(np.abs(desviacion))
md(
    rf"""
    La desviación máxima respecto a la energía inicial es de
    **{desviacion_max:.1e}** en valor relativo a lo largo de
    {len(corrida.energia_total) - 1} pasos. El ensayo
    `tests/test_lennard_jones.py` fija una cota de $5\times10^{{-4}}$ para una
    corrida corta y comprueba que un paso de 0.03 la supera.
    """
)
```

## Temperatura

$T = 2K / [3(N-1)]$, con $3(N-1)$ grados de libertad porque el momento total es
nulo. En una corrida microcanónica $T$ fluctúa alrededor de su media; no está
fijada.

```python hidden
P.figure(
    P.ruleY([corrida.temperatura.mean()], strokeDasharray="4 3"),
    P.line(x=t_energia, y=corrida.temperatura[cada_5], strokeWidth=1),
    x={"label": "tiempo t"},
    y={"label": "T*"},
    grid=True,
    height=260,
)
```

```python hidden
u_truncada = (
    np.mean(
        [
            lennard_jones.energia_truncada(p, LADO, lennard_jones.CORTE)
            for p in corrida.posiciones
        ]
    )
    / N
)
cola = lennard_jones.correccion_cola(DENSIDAD)
md(
    rf"""
    Temperatura media: $\langle T^*\rangle$ =
    **{corrida.temperatura.mean():.3f}**, con desviación estándar
    {corrida.temperatura.std():.3f}.

    Como comprobación contra Verlet (1967, tabla I), con $\rho^* = 0.85$ y
    $T^* = 0.782$ la energía potencial por partícula es $-6.04$. Con las
    configuraciones de esta corrida, para el potencial truncado sin desplazar en
    $r_c = 2.5$ se obtiene $U/N$ = {u_truncada:.3f}; sumando la corrección de
    cola de largo alcance ($g = 1$ más allá de $r_c$), {cola:.3f}, resulta
    **{u_truncada + cola:.3f}**.
    """
)
```

## Función de distribución radial

$g(r)$ es la densidad local relativa a la de un gas ideal a distancia $r$ de una
partícula. Se promedia sobre las instantáneas de la producción y se calcula
hasta $L/2$, donde la mínima imagen deja de ser única. El pico cerca de $r
\approx \sigma$ y los picos siguientes, que se amortiguan hasta $g \to 1$, son
la estructura de capas de un líquido.

```python
r, g = analisis.g_de_r(corrida.posiciones[len(corrida.posiciones) // 4 :], LADO)
```

```python hidden
P.figure(
    P.ruleY([1], strokeDasharray="1 3"),
    P.line(x=r, y=g),
    x={"label": "r / σ"},
    y={"label": "g(r)"},
    grid=True,
    height=280,
)
```

## Difusión

El desplazamiento cuadrático medio (MSD) se calcula con las posiciones sin
envolver en la caja, promediando sobre las partículas y sobre todos los orígenes
de tiempo de la corrida. Para tiempos largos cumple la relación de Einstein

$$
\langle |\mathbf r(t) - \mathbf r(0)|^2 \rangle = 6\,D\,t + b,
$$

así que $D$ es un sexto de la pendiente del tramo lineal. A tiempos cortos el
movimiento es balístico ($\propto t^2$) y ese tramo se excluye del ajuste.

```python
msd = analisis.desplazamiento_cuadratico_medio(corrida.posiciones)
tiempo_msd = corrida.tiempo_cuadros[: msd.size]
VENTANA = (1.0, float(tiempo_msd[-1]))
D, ordenada = analisis.coeficiente_difusion(tiempo_msd, msd, *VENTANA)
```

```python hidden
P.figure(
    P.rectY(x1=[VENTANA[0]], x2=[VENTANA[1]], y=[msd.max()], fillOpacity=0.08),
    P.line(x=tiempo_msd, y=msd, series="MSD"),
    P.line(
        x=tiempo_msd,
        y=6 * D * tiempo_msd + ordenada,
        series=f"ajuste: D* = {D:.3f}",
        strokeDasharray="6 3",
    ),
    x={"label": "tiempo t"},
    y={"label": "MSD (σ²)"},
    grid=True,
    height=280,
)
```

```python hidden
# La unidad de D es sigma * sqrt(epsilon / m), en m^2/s para el argón.
SIGMA_ARGON = 3.405e-10
v0 = np.sqrt(119.8 * 1.380649e-23 / (39.948 * 1.66053907e-27))
md(
    rf"""
    Con el ajuste en la zona sombreada
    ($t \in [{VENTANA[0]:.0f}, {VENTANA[1]:.0f}]$), $D^*$ = **{D:.3f}** en
    unidades reducidas. Para el argón ($\sigma$ = 3.405 Å,
    $\varepsilon/k_B$ = 119.8 K, $m$ = 39.948 u) la unidad de $D$ es
    $\sigma\sqrt{{\varepsilon/m}}$ = {SIGMA_ARGON * v0:.2e} m²/s, de modo que
    $D$ = **{D * SIGMA_ARGON * v0:.2e} m²/s**.

    Es un solo valor de una sola corrida de {N} partículas: la incertidumbre
    estadística no se ha estimado.
    """
)
```

## Trayectorias

Las partículas que empiezan en la capa $z < L/4$ se proyectan sobre el plano
$xy$, con las posiciones envueltas en la caja. Cada una conserva el color de su
coordenada $x$ inicial, de modo que la mezcla de colores es la difusión que mide
el MSD.

```python hidden
cuadros = corrida.posiciones[::4] % LADO
capa = cuadros[0, :, 2] < LADO / 4
P.figure(
    P.rect(x1=[0], x2=[LADO], y1=[0], y2=[LADO], fill="none", stroke="currentColor"),
    P.dot(
        x=cuadros[:, capa, 0],
        y=cuadros[:, capa, 1],
        fill=cuadros[0, capa, 0],
        r=4,
        tip=False,
    ),
    frames=[f"t = {t:.1f}" for t in corrida.tiempo_cuadros[::4]],
    fps=20,
    digits=2,
    x={"domain": [0, LADO], "label": "x / σ"},
    y={"domain": [0, LADO], "label": "y / σ"},
    color={"scheme": "viridis"},
    width=420,
    aspectRatio=1,
)
```

## Cúmulos de potasio: enlace fuerte en segundo momento

Para metales como el potasio un potencial de pares no basta: la energía de
enlace de un átomo no es la suma de sus pares, sino que satura con el número de
vecinos. La aproximación del segundo momento de la banda de enlace fuerte lo
recoge con una raíz cuadrada:

$$
\begin{aligned}
E = \sum_i \Big[\, & A \sum_{j\neq i} e^{-p\,(r_{ij}/r_0 - 1)}\\
& - \sqrt{\textstyle\sum_{j\neq i} \xi^2\, e^{-2q\,(r_{ij}/r_0 - 1)}}\;\Big].
\end{aligned}
$$

El primer término es una repulsión de pares y el segundo la energía de banda.
Para K se usan los parámetros de Li, Blaisten-Barojas y Papaconstantopoulos
(1998, tabla II), ajustados a energías LDA de redes bcc y fcc: $A=1.51$ mRy,
$\xi=19.3$ mRy, $r_0=8.253\,a_0$, $p=10.58$ y $q=1.34$. Los cúmulos regulares de
2, 3 y 4 átomos (dímero, triángulo y tetraedro) dan a cada átomo 1, 2 y 3
vecinos, y permiten ver la dependencia con la coordinación.

```python
distancias = np.linspace(3.3, 6.0, 300)
CUMULOS = {2: "dímero", 3: "triángulo", 4: "tetraedro"}
energia_cumulo = {
    n: np.array(
        [
            tight_binding.energia_por_atomo(tight_binding.simplex_regular(n, d))
            for d in distancias
        ]
    )
    for n in CUMULOS
}
```

```python hidden
P.figure(
    P.ruleY([0], strokeDasharray="1 3"),
    *[
        P.line(
            x=distancias,
            y=energia_cumulo[n],
            series=f"{nombre} (N = {n}): mín. {energia_cumulo[n].min():.3f} eV",
        )
        for n, nombre in CUMULOS.items()
    ],
    x={"label": "distancia entre vecinos (Å)"},
    y={"label": "energía por átomo (eV)"},
    grid=True,
    height=300,
)
```

El mismo esquema de velocity Verlet, con fuerzas analíticas del potencial, mueve
un tetraedro de K perturbado. Como en el caso de Lennard-Jones, la energía total
es la comprobación: la cinética y la potencial se intercambian y la suma
permanece casi constante. Unidades: eV, Å y masa atómica; el paso es 0.5 en
unidades de 10.18 fs.

```python
rng = np.random.default_rng(4)
pos_k = tight_binding.simplex_regular(4, 4.3) + rng.normal(scale=0.1, size=(4, 3))
vel_k = rng.normal(scale=0.01, size=(4, 3))
vel_k -= vel_k.mean(axis=0)
PASO_K = 0.5
cinetica_k, potencial_k = tight_binding.integrar(
    pos_k,
    vel_k,
    dt=PASO_K,
    n_pasos=2000,
)
```

```python hidden
t_k = (PASO_K * tight_binding.TIEMPO * np.arange(cinetica_k.size) / 1000)[cada_5]
total_k = cinetica_k + potencial_k
P.figure(
    P.line(x=t_k, y=cinetica_k[cada_5], series="cinética"),
    P.line(
        x=t_k,
        y=(potencial_k - potencial_k.mean())[cada_5],
        series="potencial (menos su media)",
    ),
    P.line(
        x=t_k, y=(total_k - total_k.mean())[cada_5], series="total (menos su media)"
    ),
    x={"label": "tiempo (ps)"},
    y={"label": "energía (eV)"},
    grid=True,
    height=300,
)
```

```python hidden
md(
    f"""
    En los 2000 pasos la energía total oscila en {np.ptp(total_k):.1e} eV de
    pico a pico, {np.ptp(total_k) / np.ptp(cinetica_k):.1e} veces la oscilación
    de la cinética.
    """
)
```

## Referencias

- L. Verlet, _Computer "Experiments" on Classical Fluids. I. Thermodynamical
  Properties of Lennard-Jones Molecules_, Phys. Rev. **159**, 98 (1967).
  doi:10.1103/PhysRev.159.98
- Y. Li, E. Blaisten-Barojas y D. A. Papaconstantopoulos, _Structure and
  dynamics of alkali-metal clusters and fission of highly charged clusters_,
  Phys. Rev. B **57**, 15519 (1998). doi:10.1103/PhysRevB.57.15519
- E. Hairer, Ch. Lubich y G. Wanner, _Geometric numerical integration
  illustrated by the Störmer–Verlet method_, Acta Numerica **12**, 399 (2003).
  doi:10.1017/S0962492902000144
