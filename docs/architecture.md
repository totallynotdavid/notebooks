# Architecture

Notebooks is a `uv` workspace. Each directory under `packages/` is a topic
package with its own dependencies, notebooks, supporting modules and data. Each
directory under `lib/` is a library that topic packages share; a package lists
it as a dependency with `{ workspace = true }` in `[tool.uv.sources]`. The root
`pyproject.toml` defines the workspace and shared development tools. The
workspace lockfile is `uv.lock`.

[`lib/quire`](../lib/quire/src/quire) runs a Markdown article. It splits the
file into prose and `python` fences
([`document.py`](../lib/quire/src/quire/document.py)), runs the fences in one
namespace and captures what each prints and returns
([`execute.py`](../lib/quire/src/quire/execute.py)), and encodes the values as
markdown, text or chart specs
([`outputs.py`](../lib/quire/src/quire/outputs.py),
[`plot.py`](../lib/quire/src/quire/plot.py)). It writes one JSON document per
article; see [articles](articles.md).

## Notebook sources

A notebook lives in the package of its topic, next to the modules and data it
reads. The catalog in [`notebooks.toml`](../notebooks.toml) is the source of
truth for the site. Each `[[topics]]` table names a package by its directory
under `packages/`, and each `[[topics.notebooks]]` entry gives a notebook's id,
title, file and summary. A notebook's slug is `topic-id/notebook-id`. The site
publishes every notebook in the catalog.

[`scripts/notebooks_manifest.py`](../scripts/notebooks_manifest.py) reads the
catalog, checks ids, paths and packages, and writes the typed frontend data to
[`site/src/lib/catalog.generated.ts`](../site/src/lib/catalog.generated.ts).
Each notebook receives a source URL to the repository.

## Export pipeline

[`scripts/export_notebooks.py`](../scripts/export_notebooks.py) owns validation,
catalog generation, and article builds. The `validate` command checks only the
manifest. The `data` command regenerates the frontend catalog, and
`data --check` fails when the committed catalog is out of date without writing
it. The `export` command does not touch the catalog. It runs each article with
`quire build` and writes its document to `site/.articles/<slug>.json`. An
article whose fence raises fails the command, and its document is not written.

The pipeline runs `uv run --locked` with the package of each notebook's topic.
This keeps notebook imports scoped to the package that owns them.

```text
notebooks.toml
      |
      v
notebooks_manifest.py ----> catalog.generated.ts ----> Svelte components
      |
      v
export_notebooks.py ------> site/.articles ----------> article route
```

## Site

[`site/src/routes/+page.svelte`](../site/src/routes/+page.svelte) renders the
catalog. It loads the generated site data, applies the search and topic filters
from [`site/src/lib/filters.ts`](../site/src/lib/filters.ts), and groups the
notebooks by topic. Each card links to the notebook's article page.

The route
[`notebooks/[topic]/[id]`](../site/src/routes/notebooks/[topic]/[id]/+page.server.ts)
prerenders one page per article. At build time,
[`site/src/lib/server/article.ts`](../site/src/lib/server/article.ts) reads the
article's document, renders prose with markdown-it and KaTeX, and highlights
code with Shiki. The page ships no Python and no markdown parser. A figure whose
spec exceeds 16 KB leaves the page data: the route
[`figures/[figure].json`](../site/src/routes/notebooks/[topic]/[id]/figures/[figure].json/+server.ts)
prerenders it as its own file, and
[`LazyFigure.svelte`](../site/src/lib/components/article/LazyFigure.svelte)
reserves its estimated height and fetches it a screen before it scrolls into
view. In the browser,
[`PlotFigure.svelte`](../site/src/lib/components/article/PlotFigure.svelte)
draws each chart spec with Observable Plot
([`plot.ts`](../site/src/lib/article/plot.ts)), with the colors of the site
theme, and plays its frames.

[`site/src/routes/+layout.ts`](../site/src/routes/+layout.ts) enables
prerendering. The SvelteKit adapter produces a static site in `site/build`. The
deployment workflow in
[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) generates the
catalog, builds the articles, then builds that directory for GitHub Pages.

[`layout.md`](layout.md) defines the folder map and site build boundary. `site/`
contains only the frontend and generated site inputs. Notebook source, data,
documentation, and build tooling remain outside it.

## Package dependencies

Each package `pyproject.toml` owns the dependencies of its notebooks. The
remote-sensing package declares rasterio as a normal dependency for its raster
article. Package requirements are documented in
[`environment.md`](environment.md).
