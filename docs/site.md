# Site

The site is a prerendered SvelteKit application in [`site/`](../site/). The
catalog generator writes the topic and notebook data to a committed file that
the site build reads. Before a site build, follow the catalog validation, data
generation, and export workflow in [`notebooks.md`](notebooks.md).

Install the dependencies (see [`environment.md`](environment.md)), then export
the notebooks and build the site:

```sh
mise run build
```

The build writes the static site to `site/build`. Check the site's code with
`mise run lint:web`, `mise run typecheck` and `mise run test:web`. After
generating the catalog data and exported notebook assets as described in
[`notebooks.md`](notebooks.md), start the Vite development server:

```sh
bun run --cwd site dev
```

Run the export command before opening a notebook in the development server. An
article page reads `site/.articles`, and a marimo page is a file in
`site/static/notebooks`; both are gitignored. To preview one article while you
edit it, see [articles](articles.md).
