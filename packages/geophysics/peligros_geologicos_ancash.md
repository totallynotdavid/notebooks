```python hidden
import json
import textwrap
from collections import Counter
from pathlib import Path

import numpy as np
import shapely
from quire import md
from quire import plot as P

DATOS = Path(__file__).resolve().parent / "data" / "ancash"


def tabla(encabezado, filas):
    """Tabla Markdown con la primera columna a la izquierda y el resto a la derecha."""
    return md(
        "\n".join(
            [
                "| " + " | ".join(encabezado) + " |",
                "| --- |" + " ---: |" * (len(encabezado) - 1),
                *("| " + " | ".join(map(str, fila)) + " |" for fila in filas),
            ]
        )
    )


def envolver(texto, ancho=34):
    """Parte una etiqueta larga en líneas; Plot dibuja cada línea del eje."""
    return textwrap.fill(texto, ancho)
```

# Movimientos en masa en Áncash

Este artículo usa el inventario nacional de peligros geológicos de INGEMMET para
responder tres preguntas sobre Áncash:

- qué movimientos en masa se han registrado y con qué frecuencia,
- qué provincias concentran más registros,
- qué factores condicionan los huaicos, es decir, los flujos de detritos y de
  lodo.

## Fuente de datos

Los datos son la capa `SERV_PELIGROS_GEOLOGICOS/MapServer/0` de GeoCatMin
(INGEMMET), filtrada con `NM_DPTO='Ancash'`. Una copia está guardada junto al
artículo y `data/ancash/NOTA.md` la describe. Para descargar los datos actuales:

```sh
uv run --package geophysics python -m ingemmet_peligros.inventario
```

```python
inventario = json.loads((DATOS / "peligros_ancash.geojson").read_text())
dominios = json.loads((DATOS / "dominios.json").read_text())
registros = [f["properties"] for f in inventario["features"]]
lon, lat = np.array([f["geometry"]["coordinates"] for f in inventario["features"]]).T


def decodificar(codigo, campo):
    return dominios[campo].get(codigo, f"{codigo} (sin descripción en el dominio)")


# Solo los códigos 1504 y 1505 representan huaicos. El aluvión y las
# avalanchas tienen otros códigos y no se cuentan.
HUAICO = {"1000|1500|1504", "1000|1500|1505"}

tipo = [decodificar(r["TIP_PELIGRO"], "TIP_PELIGRO") for r in registros]
subtipo = [
    decodificar(r["NOM_PELIGRO"], "NOM_PELIGRO") if r["NOM_PELIGRO"] else "Sin subtipo"
    for r in registros
]
provincia = [r["NM_PROV"] for r in registros]
huaico = np.array([r["NOM_PELIGRO"] in HUAICO for r in registros])
```

```python hidden
md(
    f"""
    Son {len(registros)} registros, todos puntos en WGS84 con
    {len(registros[0])} atributos. Los atributos codificados (`TIP_PELIGRO`,
    `NOM_PELIGRO`, `FACT_SITIO`, `FACT_GEOGR`, `FACT_ANTRO`) se traducen con
    los dominios de la capa. Un código que la capa usa pero que su dominio no
    define se muestra tal cual, marcado como *sin descripción en el dominio*,
    porque no hay base para inventarle un nombre.
    """
)
```

## Tipos de movimiento en masa

`COD_PELIGRO` vale `1000` (movimientos en masa) en todos los registros de Áncash
de esta capa. `TIP_PELIGRO` separa los tipos y `NOM_PELIGRO` los subtipos. Los
nombres son los del dominio, sin tildes.

```python hidden
por_tipo = Counter(tipo).most_common()
tabla(
    ["tipo", "registros", "porcentaje"],
    [[t, n, f"{n / len(tipo):.1%}"] for t, n in por_tipo],
)
```

```python hidden
por_subtipo = Counter(subtipo).most_common()
primeros = por_subtipo[:12]
P.figure(
    P.barX(
        x=[n for _, n in primeros],
        y=[envolver(s) for s, _ in primeros],
        sort={"y": "-x"},
    ),
    title="Los 12 subtipos más registrados",
    x={"label": "registros", "grid": True},
    y={"label": None},
    marginLeft=230,
    height=420,
)
```

```python hidden
sin_dominio = sum(n for s, n in por_subtipo if "sin descripción" in s)
sin_subtipo = dict(por_subtipo)["Sin subtipo"]
mayor = next(
    s for s, _ in por_subtipo if "sin descripción" not in s and s != "Sin subtipo"
)
md(
    f"""
    El subtipo con nombre más registrado es *{mayor.lower()}*. {sin_dominio}
    registros llevan un código de subtipo que el dominio de la capa no define,
    y {sin_subtipo} no tienen subtipo.
    """
)
```

## Provincias más afectadas

El conteo usa la provincia que figura en cada registro (`NM_PROV`). Los
polígonos provinciales simplificados solo se usan para dibujar el mapa.

```python
por_provincia = Counter(provincia).most_common()
huaicos_en = Counter(p for p, h in zip(provincia, huaico, strict=True) if h)
principal = {
    p: Counter(t for q, t in zip(provincia, tipo, strict=True) if q == p).most_common(
        1
    )[0][0]
    for p, _ in por_provincia
}
```

```python hidden
tabla(
    ["provincia", "registros", "huaicos", "% huaicos", "tipo principal"],
    [
        [p, n, huaicos_en[p], f"{huaicos_en[p] / n:.0%}", principal[p]]
        for p, n in por_provincia
    ],
)
```

```python hidden
nombres = [p for p, _ in por_provincia]
P.figure(
    P.barX(
        x=[huaicos_en[p] for p in nombres]
        + [n - huaicos_en[p] for p, n in por_provincia],
        y=nombres * 2,
        fill=["Huaicos"] * len(nombres) + ["Otros movimientos"] * len(nombres),
    ),
    title="Registros por provincia",
    x={"label": "registros", "grid": True},
    y={"label": None, "domain": nombres},
    color={"legend": True},
    marginLeft=170,
    height=480,
)
```

## Mapa sobre las provincias

```python
peru = json.loads((DATOS / "peru_provincial_simple.geojson").read_text())
contados = {p.upper(): n for p, n in por_provincia}
provincias = [
    f for f in peru["features"] if f["properties"]["NOMBPROV"].upper() in contados
]
formas = [shapely.geometry.shape(f["geometry"]) for f in provincias]
# Los polígonos simplificados requieren un margen de 0.1° para incluir
# puntos que caen justo fuera de sus límites.
area = shapely.union_all(formas).buffer(0.1)
dentro = shapely.contains_xy(area, lon, lat)
```

```python hidden
etiquetas = [forma.representative_point() for forma in formas]
nombre_de = {p.upper(): p for p, _ in por_provincia}
nombres_mapa = [nombre_de[f["properties"]["NOMBPROV"].upper()] for f in provincias]
bordes = shapely.union_all(formas).bounds
mas = max(contados.values())


def gris(n):
    """Gris más oscuro cuantos más registros tiene la provincia."""
    nivel = round(240 - 110 * n / mas)
    return f"#{nivel:02x}{nivel:02x}{nivel:02x}"


# Colores literales: el relleno de las provincias y los puntos comparten la
# escala de color de Plot, que no mezcla números con categorías.
grupo = np.where(huaico, "#d62728", "#1f77b4")
# Los otros movimientos van primero para que los huaicos queden encima.
orden = np.argsort(huaico[dentro], kind="stable")
P.figure(
    P.geo(
        [f["geometry"] for f in provincias],
        fill=[gris(contados[f["properties"]["NOMBPROV"].upper()]) for f in provincias],
        stroke="#888",
        strokeWidth=0.6,
        title=nombres_mapa,
    ),
    P.dot(
        x=lon[dentro][orden],
        y=lat[dentro][orden],
        stroke=grupo[dentro][orden],
        r=1.8,
        strokeOpacity=0.8,
        tip=False,
    ),
    P.text(
        x=[p.x for p in etiquetas],
        y=[p.y for p in etiquetas],
        text=[f"{p}\n{contados[p.upper()]}" for p in nombres_mapa],
        fontSize=9,
        fill="#222",
        stroke="white",
        strokeWidth=3,
        paintOrder="stroke",
    ),
    title="Registros por provincia y ubicación de cada punto",
    projection={
        "type": "mercator",
        "domain": {
            "type": "MultiPoint",
            "coordinates": [list(esquina) for esquina in np.reshape(bordes, (2, 2))],
        },
    },
    color={"type": "identity"},
    width=560,
)
```

Los puntos rojos son huaicos y los azules, los demás movimientos. El gris de
cada provincia crece con su número de registros.

```python hidden
fuera = [
    f"{r['COD_INV']} ({r['NM_PROV']})"
    for r, d in zip(registros, dentro, strict=True)
    if not d
]
md(
    f"""
    {len(fuera)} registro(s) tienen coordenadas fuera de Áncash y no se
    dibujan: {", ".join(fuera)}. Su provincia sí cuenta en las tablas.
    """
)
```

## Qué condiciona los huaicos

Cada registro puede citar varios factores. Los gráficos muestran qué porcentaje
de los huaicos cita cada factor, junto al porcentaje de los demás movimientos en
masa, para ver cuáles distinguen a los huaicos.

- `FACT_SITIO`: condiciones del terreno (roca, suelo, pendiente).
- `FACT_GEOGR`: entorno geográfico, donde están las lluvias y otros
  desencadenantes.
- `FACT_ANTRO`: intervención humana.

```python
def citados(campo, registro):
    """Los factores distintos que cita un registro, ya traducidos."""
    codigos = {c.strip() for c in (registro[campo] or "").split(",") if c.strip()}
    return {decodificar(c, campo) for c in codigos}


def porcentajes(campo):
    """Porcentaje de huaicos y de otros movimientos que cita cada factor."""
    grupos = {"Huaicos": huaico, "Otros movimientos": ~huaico}
    resultado = {}
    for nombre, mascara in grupos.items():
        cuenta = Counter(
            f
            for r, m in zip(registros, mascara, strict=True)
            if m
            for f in citados(campo, r)
        )
        resultado[nombre] = {f: 100 * n / mascara.sum() for f, n in cuenta.items()}
    factores = sorted(
        set(resultado["Huaicos"]) | set(resultado["Otros movimientos"]),
        key=lambda f: -resultado["Huaicos"].get(f, 0),
    )
    return {f: {g: resultado[g].get(f, 0.0) for g in grupos} for f in factores}


sitio = porcentajes("FACT_SITIO")
geografia = porcentajes("FACT_GEOGR")
antropico = porcentajes("FACT_ANTRO")
```

```python hidden
def grafico_factores(tabla, titulo):
    factores = list(tabla)
    etiquetas = [envolver(f, 40) for f in factores]
    grupos = ["Huaicos", "Otros movimientos"]
    x = [tabla[f][g] for g in grupos for f in factores]
    y = etiquetas * 2
    return P.figure(
        P.ruleY(
            y=etiquetas,
            x1=[tabla[f]["Huaicos"] for f in factores],
            x2=[tabla[f]["Otros movimientos"] for f in factores],
            stroke="#999",
        ),
        P.dot(
            x=x,
            y=y,
            fill=[g for g in grupos for _ in factores],
            r=4,
        ),
        title=titulo,
        x={
            "label": "% de los registros del grupo que citan el factor",
            "grid": True,
            "domain": [0, 100],
        },
        y={"label": None, "domain": etiquetas},
        color={"legend": True},
        marginLeft=270,
        height=40 * len(factores) + 70,
        digits=3,
    )


P.grid(
    grafico_factores(sitio, "Factores del sitio (FACT_SITIO)"),
    grafico_factores(geografia, "Entorno geográfico y desencadenantes (FACT_GEOGR)"),
)
```

Pocos registros citan factores antrópicos, así que basta una tabla:

```python hidden
tabla(
    ["factor antrópico (FACT_ANTRO)", "% de huaicos", "% de otros movimientos"],
    [
        [f, f"{v['Huaicos']:.1f}", f"{v['Otros movimientos']:.1f}"]
        for f, v in antropico.items()
    ],
)
```

```python hidden
n_huaicos = int(huaico.sum())
sin_antro = sum(
    1 for r, h in zip(registros, huaico, strict=True) if h and not r["FACT_ANTRO"]
)


def mayor_brecha(tabla):
    brechas = {
        f: v["Huaicos"] - v["Otros movimientos"]
        for f, v in tabla.items()
        if "sin descripción" not in f
    }
    factor = max(brechas, key=brechas.get)
    return factor, brechas[factor]


factor_sitio, brecha_sitio = mayor_brecha(sitio)
factor_geografia, brecha_geografia = mayor_brecha(geografia)
tres = ", ".join(f"*{f.lower()}*" for f in list(sitio)[:3])
lluvia = {
    f: geografia.get(f, {"Huaicos": 0.0})["Huaicos"]
    for f in ["Lluvias intensas", "Lluvias prolongadas"]
}
codigo_11 = decodificar("11", "FACT_GEOGR")
md(
    f"""
    Lectura de los gráficos, con {n_huaicos} huaicos:

    - Los factores del sitio que más citan los huaicos son {tres}.
    - El factor del sitio con más ventaja para los huaicos sobre los demás
      movimientos es *{factor_sitio.lower()}*, con {brecha_sitio:.0f} puntos
      porcentuales. En el entorno geográfico es *{factor_geografia.lower()}*,
      con {brecha_geografia:.0f} puntos.
    - Las lluvias intensas figuran en el {lluvia["Lluvias intensas"]:.0f} % de
      los huaicos y las prolongadas en el
      {lluvia["Lluvias prolongadas"]:.0f} %. Es poco para un flujo que se asocia
      a lluvias. El código `11` de `FACT_GEOGR` lo citan el
      {geografia[codigo_11]["Huaicos"]:.0f} % de los huaicos y el dominio de la
      capa no lo define, así que no se puede leer como lluvia ni como ningún
      otro factor.
    - {sin_antro} de los {n_huaicos} huaicos no registran ningún factor
      antrópico, así que ese campo describe pocos casos y no permite comparar
      grupos.
    """
)
```

```python hidden
anios = [r["FECHA"][:4] if r["FECHA"] else None for r in registros]
anio, n_anio = Counter(anios).most_common(1)[0]
estudio = Counter(
    r["TIESTU_ANO"] for r, a in zip(registros, anios, strict=True) if a == anio
).most_common(1)[0][0]
md(
    f"""
    ## Cómo leer estos conteos

    Es un inventario de campo, no un catálogo de eventos. {n_anio} de los
    {len(registros)} registros ({n_anio / len(registros):.0%}) tienen fecha de
    {anio} y el estudio más frecuente entre ellos es «{estudio}». Las
    diferencias entre provincias reflejan en parte dónde se hizo el trabajo de
    campo, además de dónde ocurren los movimientos. La capa no da el volumen ni
    los daños de cada evento, así que un conteo mayor no significa mayor riesgo.
    """
)
```
