```python hidden
import importlib.util
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from Py6S import AeroProfile, AtmosProfile, GroundReflectance, SixS, Wavelength
from quire import cache, md
from quire import plot as P

# Python 3.14 no puede importar `6s-bin`, así que se localiza su ejecutable.
SIXS_PATH = (
    Path(importlib.util.find_spec("sixs_bin").submodule_search_locations[0])
    / "sixsV1.1"
)

# Py6S borra la entrada temporal al terminar cada corrida. Usa el directorio
# del artículo para no escribir en el directorio temporal del sistema.
tempfile.tempdir = str(Path(__file__).resolve().parent)


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
```

# Transferencia radiativa con 6S a través de Py6S

El modelo **6S** (Second Simulation of a Satellite Signal in the Solar Spectrum)
calcula la radiancia que un sensor satelital mide sobre una superficie, dados la
atmósfera, los aerosoles y la geometría de observación. **Py6S** es la interfaz
de Python que escribe la entrada de 6S, ejecuta el programa y lee sus
resultados.

Este artículo ejecuta 6S al construir la página. El ejecutable viene compilado
en el paquete `6s-bin`, de modo que no hace falta instalar nada ni descargar
datos. Se estudia cómo cambia la señal que llega al sensor con tres variables:

- el espesor óptico de aerosoles a 550 nm (AOD),
- el contenido de vapor de agua de la columna atmosférica,
- la geometría, aquí el ángulo cenital solar.

```python
SURFACE_REFLECTANCE = 0.25
OZONE_CM_ATM = 0.25
BANDS_UM = {
    "azul (0.485 µm)": 0.485,
    "rojo (0.675 µm)": 0.675,
    "NIR (0.865 µm)": 0.865,
    "vapor de agua (0.94 µm)": 0.94,
}


@cache
def run_6s(wavelength_um, aod=0.2, water=2.5, solar_z=40.0):
    s = SixS(str(SIXS_PATH))
    s.wavelength = Wavelength(wavelength_um)
    s.aero_profile = AeroProfile.PredefinedType(AeroProfile.Continental)
    s.atmos_profile = AtmosProfile.UserWaterAndOzone(water, OZONE_CM_ATM)
    s.ground_reflectance = GroundReflectance.HomogeneousLambertian(SURFACE_REFLECTANCE)
    s.aot550 = aod
    s.geometry.solar_z = solar_z
    s.geometry.solar_a = 0.0
    s.geometry.view_z = 0.0
    s.geometry.view_a = 0.0
    # Mantener la fecha fija mantiene constante la distancia Tierra-Sol.
    s.geometry.month = 7
    s.geometry.day = 14
    s.run()
    o = s.outputs
    # Las salidas de Py6S no se pueden guardar en disco; se copian las usadas.
    return SimpleNamespace(
        apparent_reflectance=o.apparent_reflectance,
        apparent_radiance=o.apparent_radiance,
        direct_solar_irradiance=o.direct_solar_irradiance,
        diffuse_solar_irradiance=o.diffuse_solar_irradiance,
        total_gaseous_transmittance=o.total_gaseous_transmittance,
        transmittance_total_scattering=o.transmittance_total_scattering.total,
        transmittance_water=o.transmittance_water.total,
        spherical_albedo=o.spherical_albedo.total,
    )
```

## Una corrida

```python hidden
md(
    f"""
    Se fija el caso de referencia: AOD de 0.2, columna de vapor de agua de
    2.5 g/cm², ángulo cenital solar de 40°, ozono de {OZONE_CM_ATM} cm-atm y
    superficie de reflectancia {SURFACE_REFLECTANCE}. Las salidas de 6S en la
    banda roja son:
    """
)
```

```python hidden
referencia = run_6s(0.675)
tabla(
    ["salida", "valor"],
    [
        ["Reflectancia aparente (sensor)", f"{referencia.apparent_reflectance:.4f}"],
        [
            "Radiancia en el sensor (W m⁻² sr⁻¹ µm⁻¹)",
            f"{referencia.apparent_radiance:.3f}",
        ],
        [
            "Irradiancia solar directa (W m⁻² µm⁻¹)",
            f"{referencia.direct_solar_irradiance:.3f}",
        ],
        [
            "Irradiancia solar difusa (W m⁻² µm⁻¹)",
            f"{referencia.diffuse_solar_irradiance:.3f}",
        ],
        [
            "Transmitancia total por dispersión",
            f"{referencia.transmittance_total_scattering:.4f}",
        ],
        [
            "Transmitancia gaseosa total",
            f"{referencia.total_gaseous_transmittance:.4f}",
        ],
        ["Albedo esférico de la atmósfera", f"{referencia.spherical_albedo:.4f}"],
    ],
)
```

## Malla de simulaciones

Se ejecuta 6S para cada combinación de AOD, vapor de agua, ángulo cenital solar
y banda.

```python
AOD_VALUES = [0.05, 0.2, 0.5, 1.0]
WATER_VALUES = [0.5, 2.5, 4.5]
SOLAR_ZENITH_VALUES = [20.0, 40.0, 60.0]

grid = {
    (band, aod, water, solar_z): run_6s(BANDS_UM[band], aod, water, solar_z)
    for band in BANDS_UM
    for aod in AOD_VALUES
    for water in WATER_VALUES
    for solar_z in SOLAR_ZENITH_VALUES
}
```

```python hidden
md(
    f"""
    La malla tiene **{len(grid)}** corridas: {len(AOD_VALUES)} valores de AOD,
    {len(WATER_VALUES)} de vapor de agua, {len(SOLAR_ZENITH_VALUES)} de ángulo
    cenital solar y {len(BANDS_UM)} bandas.
    """
)
```

## Efecto de los aerosoles

Con vapor de agua de 2.5 g/cm² y ángulo cenital solar de 40°, la reflectancia
aparente en el sensor cambia con el AOD así:

```python hidden
aod_table = {
    band: [grid[band, aod, 2.5, 40.0].apparent_reflectance for aod in AOD_VALUES]
    for band in BANDS_UM
}
tabla(
    ["AOD", *BANDS_UM],
    [
        [aod, *(f"{aod_table[band][i]:.4f}" for band in BANDS_UM)]
        for i, aod in enumerate(AOD_VALUES)
    ],
)
```

La animación recorre el AOD de 0 a 1 sobre el espectro VNIR, con los mismos
vapor de agua y ángulo. Los espectros ya recorridos quedan en gris.

```python hidden
aod_barrido = np.round(np.arange(0.0, 1.0001, 0.05), 2)
lam_espectro = np.round(np.linspace(0.40, 1.00, 61), 3)
espectros = np.array(
    [
        [run_6s(float(w), aod=float(aod)).apparent_radiance for w in lam_espectro]
        for aod in aod_barrido
    ]
)
P.figure(
    P.line(
        x=np.tile(lam_espectro, len(aod_barrido)),
        y=espectros.ravel(),
        z=np.repeat(aod_barrido, lam_espectro.size),
        since=np.repeat(np.arange(len(aod_barrido)) + 1, lam_espectro.size),
        stroke="currentColor",
        strokeOpacity=0.2,
        tip=False,
    ),
    P.line(x=lam_espectro, y=espectros, strokeWidth=2),
    frames=[f"AOD = {aod:.2f}" for aod in aod_barrido],
    fps=6,
    title="Espectro VNIR según el espesor óptico de aerosoles",
    x={"label": "longitud de onda (µm)"},
    y={"label": "radiancia en el sensor (W m⁻² sr⁻¹ µm⁻¹)"},
    grid=True,
)
```

```python hidden
azul = aod_table["azul (0.485 µm)"]
nir = aod_table["NIR (0.865 µm)"]
md(
    f"""
    El AOD actúa de dos formas. Aumenta la luz que la atmósfera dispersa hacia
    el sensor sin tocar la superficie, y atenúa la luz que viene de ella. Sobre
    una superficie de reflectancia {SURFACE_REFLECTANCE} domina la atenuación:
    de AOD 0.05 a 1.0 la reflectancia aparente baja de {azul[0]:.4f} a
    {azul[-1]:.4f} en el azul y de {nir[0]:.4f} a {nir[-1]:.4f} en el NIR. El
    efecto es mayor en el azul porque los aerosoles dispersan más en longitudes
    de onda cortas. Las caídas a 0.76 µm y 0.94 µm, presentes en todos los
    espectros, son la absorción del oxígeno y del vapor de agua.
    """
)
```

## Efecto del vapor de agua

El vapor de agua absorbe en bandas puntuales. A 0.94 µm la absorción es fuerte,
mientras que en el azul y el rojo es despreciable. Esto se ve en la
transmitancia del agua para un AOD de 0.2 y un ángulo cenital solar de 40°:

```python hidden
tabla(
    ["agua (g/cm²)", *BANDS_UM],
    [
        [
            water,
            *(
                f"{grid[band, 0.2, water, 40.0].transmittance_water:.4f}"
                for band in BANDS_UM
            ),
        ]
        for water in WATER_VALUES
    ],
)
```

```python hidden
agua = np.linspace(0.25, 5.0, 20)
P.figure(
    *(
        P.line(
            x=agua,
            y=[
                run_6s(BANDS_UM[band], water=float(w)).apparent_reflectance
                for w in agua
            ],
            series=band,
            marker="circle",
        )
        for band in ("NIR (0.865 µm)", "vapor de agua (0.94 µm)")
    ),
    title="Reflectancia aparente según el vapor de agua",
    x={"label": "vapor de agua de la columna (g/cm²)"},
    y={"label": "reflectancia aparente"},
    grid=True,
)
```

## Efecto de la geometría

Un ángulo cenital solar mayor reduce la irradiancia que llega al suelo y alarga
el camino de la luz por la atmósfera. La radiancia en el sensor, para AOD de 0.2
y vapor de agua de 2.5 g/cm², es:

```python hidden
cenital = np.arange(0.0, 76.0, 5.0)
P.figure(
    *(
        P.line(
            x=cenital,
            y=[run_6s(wavelength, solar_z=float(z)).apparent_radiance for z in cenital],
            series=band,
            marker="circle",
        )
        for band, wavelength in BANDS_UM.items()
    ),
    title="Radiancia según el ángulo cenital solar",
    x={"label": "ángulo cenital solar (°)"},
    y={"label": "radiancia en el sensor (W m⁻² sr⁻¹ µm⁻¹)"},
    grid=True,
)
```
