```python hidden
import struct
from decimal import Decimal
from fractions import Fraction

import numpy as np
from quire import md
from quire import plot as P
```

# Error de punto flotante

Un número real se guarda como $(-1)^s\,(1.m)_2\times2^{e}$: un signo, un
exponente y una mantisa de longitud fija. Solo unos cuantos reales caben, y el
resto se redondea al más cercano. De ahí salen todos los errores de este
cuaderno.

| tipo   | NumPy     | Fortran            | signo |       exponente | mantisa |
| ------ | --------- | ------------------ | ----: | --------------: | ------: |
| simple | `float32` | `real`             |     1 |   8 (sesgo 127) |      23 |
| doble  | `float64` | `double precision` |     1 | 11 (sesgo 1023) |      52 |

El `float` de Python es un `float64`.

## Representación binaria

Un entero se convierte a base 2 dividiendo entre 2 y juntando los restos, del
último al primero. La conversión inversa suma $r_i2^i$.

```python
def a_binario(n):
    if n == 0:
        return "0"
    restos = []
    while n:
        restos.append(str(n % 2))
        n //= 2
    return "".join(reversed(restos))


def de_binario(cadena):
    return sum(int(r) * 2**i for i, r in enumerate(reversed(cadena)))


assert all(a_binario(n) == bin(n)[2:] for n in range(2000))
assert all(de_binario(a_binario(n)) == n for n in range(2000))

filas = [
    f"| {n} | `{a_binario(n)}` | `{bin(n)[2:]}` | {de_binario(a_binario(n))} |"
    for n in [0, 1, 5, 10, 255, 1000, 2**20 + 1]
]
md(
    "\n".join(
        [
            "| $n$ | división entre 2 | `bin(n)` | de vuelta a decimal |",
            "|---:|---|---|---:|",
            *filas,
        ]
    )
)
```

Los dos algoritmos coinciden con `bin` e `int(·, 2)` para los enteros de 0
a 1999.

Las fracciones son más delicadas: $\tfrac1{10}$ no tiene desarrollo binario
finito ($0.0\overline{0011}_2$), igual que $\tfrac13$ no tiene uno decimal
finito. `float.hex` muestra el número que realmente se guarda, exacto, como una
mantisa hexadecimal y un exponente de 2, y `Decimal(x)` muestra su valor decimal
exacto.

```python
def campos64(x):
    """Signo, exponente y mantisa de un float64 como cadenas de bits."""
    (bits,) = struct.unpack(">Q", struct.pack(">d", x))
    texto = f"{bits:064b}"
    return texto[0], texto[1:12], texto[12:]


def campos32(x):
    (bits,) = struct.unpack(">I", struct.pack(">f", x))
    texto = f"{bits:032b}"
    return texto[0], texto[1:9], texto[9:]


valores = [
    ("1", 1.0),
    ("0.5", 0.5),
    ("0.1", 0.1),
    ("0.1+0.2", 0.1 + 0.2),
    ("0.3", 0.3),
]
for nombre, valor in valores:
    print(f"{nombre:>7}  {float.hex(valor)}\n         {Decimal(valor)}")
```

Estos son sus bits en `float64`, separados en signo, exponente y mantisa, y los
de $0.1$ en `float32`:

```python
for nombre, valor in valores:
    print(f"{nombre:>7} {' '.join(campos64(valor))}")
s, e, m = campos32(0.1)
print(f"\nfloat32 {s} {e} {m}")
print(f"        = {Decimal(struct.unpack('>f', struct.pack('>f', 0.1))[0])}")
```

`0.1 + 0.2` y `0.3` difieren en el último dígito hexadecimal (`...34` y
`...33`): son dos números de `float64` vecinos, y `0.1 + 0.2 == 0.3` es falso.
Para comparar resultados de punto flotante se usa una tolerancia, no `==`.

## Épsilon de máquina

El épsilon de máquina $\varepsilon$ es la distancia entre $1$ y el siguiente
número representable: $2^{-23}$ en `float32` y $2^{-52}$ en `float64`. Un número
$x$ guardado con redondeo al más cercano tiene un error relativo de a lo sumo
$\varepsilon/2$ (la _unidad de redondeo_).

El algoritmo clásico divide $e$ entre 2 mientras $1+e>1$. Este es su resultado y
el de `numpy.finfo`:

```python
def epsilon_por_biseccion(tipo):
    """Divide e entre 2 mientras 1 + e > 1. Devuelve el último e y el previo."""
    uno = tipo(1)
    e = tipo(1)
    previo = e
    while uno + e > uno:
        previo = e
        e = e / tipo(2)
    return e, previo


filas = []
for tipo in (np.float32, np.float64):
    final, previo = epsilon_por_biseccion(tipo)
    info = np.finfo(tipo)
    filas.append(
        f"| `{tipo.__name__}` | {float(final):.4e} | {float(previo):.4e} "
        f"| {float(info.eps):.4e} "
        f"| {float(info.tiny):.3e} | {float(info.max):.3e} | {info.precision} |"
    )
md(
    "\n".join(
        [
            "| tipo | último $e$ del bucle | $e$ previo | `finfo.eps` | `tiny` | `max` | cifras |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

El bucle termina en el primer $e$ con $1+e=1$, que es $\varepsilon/2$:
$1+\varepsilon/2$ está a medio camino entre dos números y el redondeo al par lo
manda de vuelta a $1$. El valor anterior, $e$ previo, sí es $\varepsilon$. Un
programa que imprime el último $e$ del bucle informa $\varepsilon/2$, la mitad
del épsilon de máquina.

`numpy.finfo` da $\varepsilon$ directamente. `tiny` es el menor normal positivo,
`max` el mayor número finito y `cifras` las cifras decimales que el tipo
garantiza.

El épsilon es la separación solo cerca de $1$. En general la separación entre
vecinos crece con $|x|$, `numpy.spacing(x)`, de modo que el error _relativo_ se
mantiene y el _absoluto_ no:

```python
filas = []
for valor in [1.0, 1e3, 1e8, 2.0**24, 2.0**53]:
    s32 = float(np.spacing(np.float32(valor)))
    s64 = float(np.spacing(np.float64(valor)))
    filas.append(
        f"| {valor:.6g} | {s32:.3e} | {s32 / valor:.2e} | {s64:.3e} | {s64 / valor:.2e} |"
    )
md(
    "\n".join(
        [
            "| $x$ | `spacing`, `float32` | relativo | `spacing`, `float64` | relativo |",
            "|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

En `float32`, $2^{24}=16\,777\,216$ es el primer entero que no tiene sucesor
entero: $2^{24}+1$ se redondea a $2^{24}$. En `float64` ocurre en $2^{53}$.

## Acumulación de errores de redondeo: sumar 0.00001 muchas veces

Se suma $10^{-5}$ diez mil veces a $1$. El valor exacto de la suma de los
números decimales $1+10^4\cdot10^{-5}$ es $1.1$. Cuatro variantes:

1. acumulador `float64` y sumando `float64`;
2. acumulador `float64` y sumando `float32` ($10^{-5}$ redondeado a simple, el
   efecto de escribir `0.00001` en un programa Fortran de doble precisión: una
   constante real es de precisión simple);
3. todo en `float32`;
4. todo en `float32`, sumando primero 100 grupos de 100 sumandos y después los
   grupos (suma por bloques).

```python
def suma_naiva(valor, acumulador, n):
    total = acumulador
    for _ in range(n):
        total = total + valor
    return total


def suma_por_bloques(valor, acumulador, bloques, tamano):
    total = acumulador
    for _ in range(bloques):
        parcial = type(valor)(0)
        for _ in range(tamano):
            parcial = parcial + valor
        total = total + parcial
    return total


resultados_suma = {
    "1. `float64` + `float64`": float(
        suma_naiva(np.float64(1e-5), np.float64(1.0), 10_000)
    ),
    "2. `float64` + `float32`": float(
        suma_naiva(np.float64(np.float32(1e-5)), np.float64(1.0), 10_000)
    ),
    "3. todo `float32`": float(suma_naiva(np.float32(1e-5), np.float32(1.0), 10_000)),
    "4. `float32` por bloques": float(
        suma_por_bloques(np.float32(1e-5), np.float32(1.0), 100, 100)
    ),
}
md(
    "\n".join(
        [
            "| variante | resultado | $\\lvert\\mathrm{resultado}-1.1\\rvert$ |",
            "|---|---:|---:|",
            *[
                f"| {n} | {v!r} | {abs(v - 1.1):.1e} |"
                for n, v in resultados_suma.items()
            ],
        ]
    )
)
```

```python hidden
unidad = float(np.float32(1e-5))
md(
    f"""
    $10^{{-5}}$ en `float32` es {unidad!r}, que difiere de $10^{{-5}}$ en
    {abs(unidad - 1e-5) / 1e-5:.1e} en relación. Esa diferencia se repite diez
    mil veces y da el error de la variante 2, que es un error de
    _representación_, no de acumulación: es del orden de $\\varepsilon_{{32}}/2$
    por cada sumando. En la variante 3 el error crece mucho más porque cada suma
    redondea el resultado a 24 bits.
    """
)
```

Para ver el crecimiento se suma $10^{-5}$ en `float32` hasta $N=2\times10^5$ de
tres maneras y se compara con la suma exacta de los mismos sumandos: acumulando
en serie, con la suma por pares de NumPy (`numpy.sum`) y acumulando en serie en
`float64`.

```python
N_MAX = 200_000
unidad32 = np.float32(1e-5)
paso = np.full(N_MAX, unidad32)


def error_exacto(suma, n):
    exacta = 1 + n * Fraction(float(unidad32))
    return float(abs(Fraction(float(suma)) - exacta))


ns_suma = np.unique(np.logspace(1, np.log10(N_MAX), 40).astype(int))
serie32 = np.cumsum(np.concatenate([[np.float32(1.0)], paso]), dtype=np.float32)
serie64 = np.cumsum(np.concatenate([[1.0], paso.astype(np.float64)]), dtype=np.float64)
error_suma = {
    "serie, float32": np.array([error_exacto(serie32[n], n) for n in ns_suma]),
    "serie, float64": np.array([error_exacto(serie64[n], n) for n in ns_suma]),
    "por pares, float32": np.array(
        [
            error_exacto(np.sum(np.concatenate([[np.float32(1.0)], paso[:n]])), n)
            for n in ns_suma
        ]
    ),
}
```

```python hidden
P.figure(
    *(
        P.line(x=ns_suma[e > 0], y=e[e > 0], series=nombre, marker="dot")
        for nombre, e in error_suma.items()
        if e.any()
    ),
    P.line(
        x=ns_suma,
        y=np.finfo(np.float32).eps / 2 * ns_suma,
        series="N ε₃₂/2",
        strokeDasharray="2 3",
    ),
    title="Error de 1 + N·10⁻⁵ (los sumandos son float32)",
    x={"label": "N sumandos de 10⁻⁵", "type": "log"},
    y={"label": "error absoluto de la suma", "type": "log"},
    grid=True,
)
```

```python hidden
i = len(ns_suma) - 1
md(
    f"""
    En $N={ns_suma[i]}$ el error de la serie en `float32` es
    {error_suma["serie, float32"][i]:.1e}, el de la suma por pares
    {error_suma["por pares, float32"][i]:.1e} y el de `float64`
    {error_suma["serie, float64"][i]:.1e}. Cada suma en serie redondea un
    resultado de tamaño $\\approx1$, de modo que cada sumando de $10^{{-5}}$
    pierde cifras: ese es el error de _absorción_. La suma por pares suma
    primero números de tamaño parecido, y su error se queda en el redondeo del
    resultado final ($\\sim\\varepsilon_{{32}}$). En `float64` la suma sale
    exacta: cada sumando tiene 24 bits significativos y $N\\le2^{{18}}$
    sumandos necesitan a lo sumo 42 bits, menos que los 53 de la mantisa, así
    que su error es cero y no aparece en la gráfica.
    """
)
```

## Absorción: un término pequeño que desaparece

Se evalúa $d(\theta)=\cos 1-\tfrac12\theta\sin 1$ para
$\theta=10^{-1},10^{-2},\ldots,10^{-12}$ (el desarrollo de Taylor de
$\cos(1+\theta/2)$ a primer orden en $\theta$). Cuando $\tfrac12\theta\sin 1$ es
menor que la mitad de la separación entre números cercanos a $\cos1\approx0.54$,
restarlo no cambia el resultado: $d(\theta)=\cos 1$.

```python
filas = []
primera32 = primera64 = None
theta32, theta64 = np.float32(0.1), 0.1
cos32, sin32 = np.cos(np.float32(1)), np.sin(np.float32(1))
for k in range(1, 13):
    efecto32 = float(cos32 - (cos32 - np.float32(0.5) * theta32 * sin32))
    efecto64 = float(np.cos(1.0) - (np.cos(1.0) - 0.5 * theta64 * np.sin(1.0)))
    termino = 0.5 * float(theta32) * float(np.sin(1.0))
    if primera32 is None and efecto32 == 0:
        primera32 = k
    if primera64 is None and efecto64 == 0:
        primera64 = k
    filas.append(
        f"| $10^{{-{k}}}$ | {termino:.3e} | {efecto32:.3e} "
        f"| {abs(efecto32 - termino) / termino:.1e} | {efecto64:.3e} |"
    )
    theta32 = theta32 / np.float32(10)
    theta64 = theta64 / 10
md(
    "\n".join(
        [
            "| $\\theta$ | $\\tfrac12\\theta\\sin1$ | $\\cos1-d$, `float32` | error relativo | $\\cos1-d$, `float64` |",
            "|---:|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

```python hidden
md(
    f"En `float32` el término se pierde por completo desde $\\theta=10^{{-{primera32}}}$. "
    + (
        "En `float64` no se pierde en este rango ($10^{-12}\\gg\\varepsilon_{64}$)."
        if primera64 is None
        else f"En `float64` se pierde desde $\\theta=10^{{-{primera64}}}$."
    )
)
```

Antes de desaparecer, el término ya sale con error en `float32`: el error
relativo del efecto de $\theta$ crece al bajar $\theta$, porque lo que se resta
es del tamaño de la separación entre números cercanos a $\cos1$.

## Cancelación: restar números casi iguales

La resta de dos números cercanos es exacta, pero deja visible el error que ya
tenían. Para $x$ pequeño, $1-\cos x\approx x^2/2$ se calcula restando dos
números cercanos a $1$, de modo que $\cos x$ guarda solo unas pocas cifras de lo
que importa. La identidad $1-\cos x=2\sin^2(x/2)$ evita la resta. El cociente
$(1-\cos x)/x^2$ debe tender a $\tfrac12$.

```python
filas = []
for k in range(1, 11):
    x = 10.0**-k
    directa = (1 - np.cos(x)) / x**2
    estable = 2 * np.sin(x / 2) ** 2 / x**2
    x32 = np.float32(x)
    directa32 = (np.float32(1) - np.cos(x32)) / x32**2
    filas.append(
        f"| $10^{{-{k}}}$ | {directa32:.6f} | {directa:.12f} | {estable:.12f} |"
    )
md(
    "\n".join(
        [
            "| $x$ | directa, `float32` | directa, `float64` | $2\\sin^2(x/2)/x^2$ |",
            "|---:|---:|---:|---:|",
            *filas,
        ]
    )
)
```

La fórmula directa pierde cifras al reducir $x$ y acaba en $0$ cuando $\cos x$
se redondea a $1$ (alrededor de $x\lesssim\sqrt{\varepsilon}$: $10^{-4}$ en
`float32`, $10^{-8}$ en `float64`). La forma con $\sin^2$ da $0.5$ con todas sus
cifras. Es la misma causa que el piso de redondeo en la derivación numérica:
restar valores casi iguales y dividir entre un número pequeño.
