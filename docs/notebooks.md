# Notebooks

A notebook is a Markdown [article](articles.md) listed in
[`notebooks.toml`](../notebooks.toml). The package of its topic owns its
dependencies. The site publishes every notebook in the catalog.

## Catalog entries

Add a notebook to `notebooks.toml` under the `[[topics]]` table of its package.
For a new topic, create the package under `packages/` with its `pyproject.toml`,
then add a `[[topics]]` table whose `id` is the package directory. The `file`
path is relative to the package directory and must end in `.md`.

After changing the catalog, validate it and regenerate the site data, then
commit the regenerated `site/src/lib/catalog.generated.ts`.
`mise run lint:catalog` fails when that file is out of date:

```sh
uv run python scripts/export_notebooks.py validate
mise run data
```

The export command builds every article in the catalog into `site/.articles`. It
stops at the first article whose fence raises:

```sh
uv run python scripts/export_notebooks.py export --clean
```

## Tests

Each package with tests has a task named after it. `mise run test` runs them
all, with the export script and site tests:

| Task                                | What it checks                                                                                             |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `mise run test:numerical-methods`   | Runs the differentiation, root finding, interpolation and floating-point articles and checks their numbers |
| `mise run test:statistical-physics` | The molecular dynamics modules, and the hypersphere and Ising articles                                     |
| `mise run test:remote-sensing`      | The offline GaoFen-1 atmospheric correction                                                                |
| `mise run test:geophysics`          | The `tsunamis` module, the INGEMMET hazard inventory download and the FDSN acquisition article             |
| `mise run test:scripts`             | The catalog and export scripts                                                                             |

A test runs an article with `quire.article_namespace` and reads the names its
fences define.
