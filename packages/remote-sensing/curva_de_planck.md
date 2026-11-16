```python hidden
import numpy as np
from quire import md
from quire import plot as P
```

# Curva de Planck

La radiancia espectral de un cuerpo negro a temperatura $T$ es

$$
B_\lambda(T) = \frac{2hc^2}{\lambda^5}\,\frac{1}{e^{hc/(\lambda k T)} - 1}.
$$

Con $\lambda$ en metros, la fórmula da W/(m²·sr·m). En todo el artículo se usa
**W/(m²·sr·nm)**: la longitud de onda va en nm y el resultado se multiplica por
$10^{-9}$, de modo que valores, etiquetas y límites de los ejes comparten una
sola unidad.

Boyer deduce este espectro solo con termodinámica aplicada al oscilador
armónico: las dos primeras leyes dan el teorema de desplazamiento de Wien (la
energía del oscilador es función de $T/\omega$) y la tercera ley, con la
entropía como función analítica, fija la forma de Planck. A alta temperatura la
energía del oscilador coincide con el resultado de equipartición, que es el
límite de Rayleigh–Jeans (Boyer, _Eur. J. Phys._ 40, 2019, doi
10.1088/1361-6404/aaf45b; se leyó la versión arXiv:1809.09093).

```python
# Constantes SI exactas.
H = 6.62607015e-34  # J s
C = 299792458.0  # m/s
K = 1.380649e-23  # J/K
SIGMA = 5.670374419e-8  # W/(m^2 K^4)
TEMPERATURAS = [2000, 6000, 10000, 14000]


def planck(lam_nm, T):
    """Devuelve la radiancia en W/(m^2 sr nm) para longitudes en nm."""
    lam = lam_nm * 1e-9
    with np.errstate(over="ignore"):
        return 1e-9 * 2 * H * C**2 / lam**5 / np.expm1(H * C / (lam * K * T))


def rayleigh_jeans(lam_nm, T):
    lam = lam_nm * 1e-9
    return 1e-9 * 2 * C * K * T / lam**4


def wien(lam_nm, T):
    lam = lam_nm * 1e-9
    return 1e-9 * 2 * H * C**2 / lam**5 * np.exp(-H * C / (lam * K * T))
```

## Curvas para cuatro temperaturas

Para $\lambda \to 0$ el exponente desborda a infinito y $B_\lambda$ da cero, que
es el límite correcto. En escala logarítmica la cola de onda corta, donde
$B_\lambda$ cae por debajo de 1 W/(m²·sr·nm), queda fuera del eje.

```python hidden
lam_nm = np.linspace(1.0, 4000.0, 800)


def curvas(minimo):
    marcas = []
    for T in TEMPERATURAS:
        b = planck(lam_nm, T)
        visible = b >= minimo
        marcas.append(P.line(x=lam_nm[visible], y=b[visible], series=f"{T} K"))
    return marcas


P.grid(
    P.figure(
        *curvas(0),
        title="Escala lineal",
        x={"label": "λ (nm)", "domain": [0, 2000]},
        y={"label": "B_λ (W m⁻² sr⁻¹ nm⁻¹)", "domain": [0, 2.5e6]},
        clip=True,
        grid=True,
    ),
    P.figure(
        *curvas(1),
        title="Escala logarítmica en el eje vertical",
        x={"label": "λ (nm)", "domain": [0, 4000]},
        y={"label": None, "type": "log", "domain": [1, 1e7]},
        clip=True,
        grid=True,
    ),
)
```

## Desplazamiento de Wien

Derivando $B_\lambda$ respecto a $\lambda$ el máximo cumple $x = 5(1 - e^{-x})$
con $x = hc/(\lambda_{\max} k T)$. De ahí $\lambda_{\max} T = b = hc/(k x)$.
Aquí se halla el máximo de la curva directamente, con una búsqueda de la sección
áurea sobre $B_\lambda$, y se compara con $b/T$. La forma $B_\lambda = T^5
f(\lambda T)$ es la información que aporta el teorema de desplazamiento de Wien,
que Boyer obtiene de las dos primeras leyes de la termodinámica.

```python
def maximo(f, a, b, iteraciones=200):
    """Abscisa del máximo de una función unimodal en [a, b]."""
    razon = (np.sqrt(5) - 1) / 2
    c = b - razon * (b - a)
    d = a + razon * (b - a)
    for _ in range(iteraciones):
        if f(c) > f(d):
            b = d
        else:
            a = c
        c = b - razon * (b - a)
        d = a + razon * (b - a)
    return (a + b) / 2


# Resuelve x = 5 (1 - exp(-x)) por iteración de punto fijo.
x_wien = 5.0
for _ in range(100):
    x_wien = 5 * (1 - np.exp(-x_wien))
b_wien_mk = H * C / (K * x_wien)

lam_max = {
    T: maximo(lambda lam, T=T: planck(lam, T), 10.0, 20000.0) for T in TEMPERATURAS
}
```

```python hidden
md(
    "\n".join(
        [
            rf"$x$ = {x_wien:.9f}, $b = hc/(kx)$ = {b_wien_mk * 1e3:.9f} × 10⁻³ m·K.",
            "",
            "| T (K) | λ_max numérico (nm) | b/T (nm) | B(λ_max) (W/(m²·sr·nm)) |",
            "| ---: | ---: | ---: | ---: |",
            *[
                f"| {T} | {lam_max[T]:.2f} | {b_wien_mk / T * 1e9:.2f}"
                f" | {planck(lam_max[T], T):.4g} |"
                for T in TEMPERATURAS
            ],
        ]
    )
)
```

La animación recorre la temperatura de 2000 a 14000 K. El punto marca el máximo
numérico de cada curva y la línea vertical, $b/T$: los dos se mueven juntos
hacia el ultravioleta mientras la altura del máximo crece como $T^5$. Las curvas
ya recorridas quedan en gris.

```python hidden
T_BARRIDO = np.arange(2000, 14001, 500)
lam_barrido = np.geomspace(100.0, 5000.0, 160)
picos = np.array(
    [maximo(lambda lam, T=T: planck(lam, T), 10.0, 20000.0) for T in T_BARRIDO]
)
curvas_barrido = np.array([planck(lam_barrido, T) for T in T_BARRIDO])
cuadro = np.arange(len(T_BARRIDO))
P.figure(
    P.line(
        x=np.tile(lam_barrido, len(T_BARRIDO)),
        y=curvas_barrido.ravel(),
        z=np.repeat(T_BARRIDO, lam_barrido.size),
        since=np.repeat(cuadro + 1, lam_barrido.size),
        stroke="currentColor",
        strokeOpacity=0.2,
        tip=False,
    ),
    P.ruleX(x=(b_wien_mk / T_BARRIDO * 1e9)[:, None], strokeDasharray="4 3"),
    P.line(
        x=lam_barrido,
        y=curvas_barrido,
        strokeWidth=2,
    ),
    P.dot(
        x=picos[:, None], y=planck(picos, T_BARRIDO)[:, None], r=5, fill="currentColor"
    ),
    frames=[f"T = {T} K" for T in T_BARRIDO],
    fps=12,
    x={"label": "λ (nm)", "type": "log"},
    y={"label": "B_λ (W m⁻² sr⁻¹ nm⁻¹)", "type": "log", "domain": [1e2, 1e7]},
    clip=True,
    grid=True,
)
```

## Límites de Rayleigh–Jeans y de Wien

Con $x = hc/(\lambda k T)$:

- $x \ll 1$ (λ grande): $e^x - 1 \approx x$ y $B_\lambda \to 2ckT/\lambda^4$
  (Rayleigh–Jeans, equipartición clásica).
- $x \gg 1$ (λ pequeña): $e^x - 1 \approx e^x$ y $B_\lambda \to
  (2hc^2/\lambda^5)\,e^{-x}$ (Wien).

Las razones $B^{RJ}/B$ y $B^{W}/B$ valen $(e^x-1)/x$ y $1-e^{-x}$.

```python
T_LIMITES = 6000
lam_log = np.geomspace(10.0, 1e5, 600)
b_planck = planck(lam_log, T_LIMITES)
b_rj = rayleigh_jeans(lam_log, T_LIMITES)
b_wien = wien(lam_log, T_LIMITES)
```

```python hidden
visible = b_planck > 1e-6
with np.errstate(divide="ignore", invalid="ignore"):
    razon_rj = b_rj / b_planck
    razon_w = b_wien / b_planck
# Rayleigh-Jeans/Planck crece sin cota hacia la onda corta; un trazo que sale
# millones de veces del eje no se dibuja.
cerca = razon_rj < 3
P.grid(
    P.figure(
        P.line(
            x=lam_log[visible], y=b_planck[visible], series="Planck", strokeWidth=2.5
        ),
        P.line(x=lam_log, y=b_rj, series="Rayleigh–Jeans", strokeDasharray="6 3"),
        P.line(
            x=lam_log[visible], y=b_wien[visible], series="Wien", strokeDasharray="6 3"
        ),
        title=f"Planck y sus límites a {T_LIMITES} K",
        x={"label": "λ (nm)", "type": "log"},
        y={"label": "B_λ (W m⁻² sr⁻¹ nm⁻¹)", "type": "log", "domain": [1e-6, 1e9]},
        clip=True,
        grid=True,
    ),
    P.figure(
        P.ruleY([1]),
        P.line(x=lam_log[cerca], y=razon_rj[cerca], series="Rayleigh–Jeans / Planck"),
        P.line(x=lam_log[visible], y=razon_w[visible], series="Wien / Planck"),
        title="Razón con Planck",
        x={"label": "λ (nm)", "type": "log"},
        y={"label": None, "domain": [0, 2]},
        clip=True,
        grid=True,
    ),
)
```

```python hidden
# Rayleigh-Jeans sobreestima por menos de 5 % para lambda >= lam_rj.
# Wien subestima por menos de 5 % para lambda <= lam_w.
lam_rj = lam_log[np.abs(razon_rj - 1) < 0.05].min()
lam_w = lam_log[np.abs(razon_w - 1) < 0.05].max()
md(
    f"""
    A {T_LIMITES} K, Rayleigh–Jeans reproduce a Planck con error menor que 5 %
    para λ ≥ {lam_rj:.0f} nm y Wien para λ ≤ {lam_w:.0f} nm. Entre ambos
    valores ninguno de los dos límites basta y hay que usar la fórmula completa.
    """
)
```

### La catástrofe ultravioleta

Rayleigh–Jeans crece como $\lambda^{-4}$ y su integral diverge al acercarse
$\lambda$ a cero. Con $M = \pi\int_{\lambda_{\min}}^\infty B_\lambda\,d\lambda$
(exitancia radiante), el límite clásico no converge y Planck sí:

```python
def exitancia(f, lam_min_nm, T, lam_max_nm=1e9):
    """Integra pi por f en W/(m^2) sobre una malla logarítmica."""
    lam = np.geomspace(lam_min_nm, lam_max_nm, 20_001)
    return np.pi * np.trapezoid(f(lam, T) * lam, np.log(lam))


def exitancia_rj(lam_min_nm, T):
    # La integral clásica diverge al extender la malla hasta lambda = 0.
    lam = lam_min_nm * 1e-9
    return np.pi * 2 * C * K * T / (3 * lam**3)
```

```python hidden
md(
    "\n".join(
        [
            f"Exitancia a {T_LIMITES} K, con $\\sigma T^4$ ="
            f" {SIGMA * T_LIMITES**4:.3e} W/m²:",
            "",
            "| λ_min (nm) | Rayleigh–Jeans (W/m²) | Planck (W/m²) |",
            "| ---: | ---: | ---: |",
            *[
                f"| {lam_min} | {exitancia_rj(lam_min, T_LIMITES):.3e}"
                f" | {exitancia(planck, lam_min, T_LIMITES):.3e} |"
                for lam_min in (1000, 100, 10, 1)
            ],
        ]
    )
)
```

## Stefan–Boltzmann

La exitancia total es $M(T) = \pi\int_0^\infty B_\lambda\,d\lambda = \sigma
T^4$. Se integra numéricamente con la regla del trapecio sobre una malla
logarítmica de 1 nm a 1 m (el integrando es $B_\lambda\,\lambda$ respecto a
$\ln\lambda$) y se compara con $\sigma T^4$, donde $\sigma = 2\pi^5 k^4/(15 h^3
c^2)$.

```python
sigma_derivada = 2 * np.pi**5 * K**4 / (15 * H**3 * C**2)
T_SB = np.linspace(1000, 15000, 60)
m_sb = np.array([exitancia(planck, 1.0, T) for T in T_SB])
```

```python hidden
md(
    "\n".join(
        [
            rf"$\sigma$ desde las constantes = {sigma_derivada:.9e} W/(m²·K⁴);"
            f" valor usado = {SIGMA:.9e}.",
            "",
            "| T (K) | π∫B dλ (W/m²) | σT⁴ (W/m²) | error relativo |",
            "| ---: | ---: | ---: | ---: |",
            *[
                f"| {T} | {exitancia(planck, 1.0, T):.6e} | {SIGMA * T**4:.6e}"
                f" | {exitancia(planck, 1.0, T) / (SIGMA * T**4) - 1:+.2e} |"
                for T in TEMPERATURAS
            ],
        ]
    )
)
```

```python hidden
P.figure(
    P.line(x=T_SB, y=SIGMA * T_SB**4, series="σT⁴"),
    P.dot(x=T_SB, y=m_sb, series="integral numérica", r=3),
    x={"label": "T (K)", "type": "log"},
    y={"label": "exitancia M (W m⁻²)", "type": "log"},
    grid=True,
    height=320,
)
```
