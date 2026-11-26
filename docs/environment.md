# Environment

The repository uses the tool versions in [`mise.toml`](../mise.toml): Bun, Node,
Python, and uv. The Python workspace requires Python 3.14. Install the tools,
then the locked Python workspace and site dependencies:

```sh
mise install -y
mise run install
```

The remote-sensing raster article uses rasterio. Its package includes the
runtime libraries needed to open the committed GeoTIFF, so no system raster
installation is required. Preview the article with:

```sh
uv run --locked --package remote-sensing quire watch packages/remote-sensing/landsat_rasterio.md \
  -o site/.articles/remote-sensing/landsat-rasterio.json
```

Every article builds offline from data committed beside it. These scripts
refresh that data from external sources, and only they need a network or
credentials. The Earth Engine scripts read `EE_PROJECT` from
`packages/remote-sensing/.env`.

| Script                                                                                      | Refreshes                                                               |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [`prepare_landsat.py`](../packages/remote-sensing/prepare_landsat.py)                       | The Landsat clip, from Earth Engine                                     |
| [`prepare_earth_engine.py`](../packages/remote-sensing/prepare_earth_engine.py)             | The Earth Engine results over Peru                                      |
| [`gaofen1/prepare.py`](../packages/remote-sensing/gaofen1/prepare.py)                       | The GaoFen-1 clip and its Earth Engine inputs                           |
| [`ingemmet_peligros/inventario.py`](../packages/geophysics/ingemmet_peligros/inventario.py) | The INGEMMET hazard inventory for Ancash                                |
| [`adquisicion/fdsn.py`](../packages/geophysics/adquisicion/fdsn.py)                         | The Pisco-2007 StationXML and miniSEED, from EarthScope's FDSN services |
