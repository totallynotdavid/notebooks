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

Some notebooks need external data or credentials. Their source files state the
required inputs. The current examples are the GaoFen-1 correction in
[`gaofen1/prepare.py`](../packages/remote-sensing/gaofen1/prepare.py) and the
Earth Engine fixture script
[`prepare_earth_engine.py`](../packages/remote-sensing/prepare_earth_engine.py),
which reads `EE_PROJECT` from `packages/remote-sensing/.env`.
