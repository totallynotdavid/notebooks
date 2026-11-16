# Site

The site is a prerendered SvelteKit application in [`site/`](../site/). The
catalog generator writes the topic and notebook data to a committed file that
the site build reads. Before a site build, follow the catalog validation, data
generation, and export workflow in [`notebooks.md`](notebooks.md).

Install the dependencies (see [`environment.md`](environment.md)), then build
the articles and the site:

```sh
mise run build
```

The build writes the static site to `site/build`. Check the site's code with
`mise run lint:web`, `mise run typecheck` and `mise run test:web`. After
generating the catalog data and building the articles as described in
[`notebooks.md`](notebooks.md), start the Vite development server:

```sh
bun run --cwd site dev
```

An article page reads its document from `site/.articles`, which is gitignored,
so run the export command before opening it in the development server. To
preview one article while you edit it, see [articles](articles.md).
