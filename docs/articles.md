# Articles

An article is a Markdown file whose `python` fences run. Preview one while you
edit it: `quire watch` reruns the article on every save, and the development
server shows the result when you reload the page.

```sh
uv run --locked --package dynamics quire watch packages/dynamics/pendulo_simple.md \
  -o site/.articles/dynamics/simple-pendulum.json
bun run --cwd site dev
```

Open `/notebooks/dynamics/simple-pendulum/` on the development server. The
output path is `site/.articles/<slug>.json`, where the slug is
`topic-id/notebook-id` from the catalog. `quire build` takes the same arguments
and runs the article once. A fence that raises stops the build and prints the
traceback with line numbers of the Markdown file.

## Format

Prose is Markdown with `$...$` and `$$...$$` math. Fences run top to bottom in
one namespace, with the article's folder as the working directory and on the
import path, so an article imports the modules beside it.

````markdown
```python hidden
import numpy as np
from quire import md
from quire import plot as P
```

The period grows with the amplitude.

```python
t = np.linspace(0, 10, 200)
P.figure(P.line(x=t, y=np.sin(t), series="sin"), x={"label": "t [s]"})
```
````

A `python` fence shows its code and then its outputs. A `python hidden` fence
shows only its outputs. The site folds code longer than 14 lines behind a "Show
code" button.

A fence has up to two outputs: what it printed, then the value of its last
expression. A value of `None` shows nothing. The value becomes:

| Value                 | Output                                                                        |
| --------------------- | ----------------------------------------------------------------------------- |
| `md(text)`            | Markdown and math, so an f-string puts computed numbers into prose and tables |
| `P.figure(...)`       | A chart drawn in the browser                                                  |
| `P.grid(figure, ...)` | Charts side by side, one column on a narrow page                              |
| anything else         | Its `repr` as plain text                                                      |

`md` removes the common indentation of its text.

## Figures

[`quire.plot`](../lib/quire/src/quire/plot.py) builds an
[Observable Plot](https://observablehq.com/plot/) figure. Each mark function has
the name of a Plot mark, such as `line`, `dot`, `areaY`, `ruleY` or `link`. An
array option of a mark is a channel; any other option passes to Plot as it is.
The options of `P.figure` pass to `Plot.plot`, such as `title`, `x`, `y`,
`grid`, `width` and `aspectRatio`.

```python
P.figure(
    P.line(x=t, y=energy_rk4, series="RK4"),
    P.line(x=t, y=energy_verlet, series="velocity Verlet", strokeDasharray="6 4"),
    y={"label": "|E − E₀|/E₀", "type": "log"},
    grid=True,
)
```

`series` names a mark in the legend and gives it a color from the site's
palette, in the order the article names the series. A string array in `fill` or
`stroke` names one series per point. The site adds the legend, a tooltip on
lines, dots, areas, bars and cells, and labels log axes as powers of ten.
Figures follow the site's light and dark themes. `width` is a maximum; a figure
still shrinks with the page.

Numbers are rounded to 5 significant digits. Pass `digits=` to `P.figure` to
change it.

## Animations

A figure with `frames` animates. `frames` holds one label per frame, and `fps`
sets the speed (20 by default). A channel with one row per frame, of shape
`(frames, n)`, changes with the frame; every other channel is drawn once. The
site adds play, pause and a frame slider. An axis without a `domain` is fixed to
the range of every frame, so it does not jump.

```python
P.figure(
    P.dot(x=x, y=y, r=8, fill=names),  # x and y have shape (frames, 3)
    frames=[f"t = {s:.2f} s" for s in times],
    x={"domain": [-1.2, 1.2], "axis": None},
    y={"domain": [-1.2, 1.2], "axis": None},
    aspectRatio=1,
    width=560,
)
```

When the frames are values of a parameter rather than steps in time, name the
parameter. The reader then picks a value with a slider that starts at frame
`start`, and nothing plays:

```python
P.figure(
    P.line(x=malla, y=curvas),  # curvas has shape (len(grados), len(malla))
    frames=[f"n = {n}" for n in grados],
    parameter="grado",
    start=6,
)
```

A channel whose element count changes between frames is padded with NaN to the
longest frame; Plot skips the NaN points.

Every frame is stored in the article, so keep frames few and rounded. A figure
larger than 16 KB loads from its own file as it nears the view; see
[architecture.md](architecture.md).

## Cache

`quire.cache` keeps a slow function's results between builds, so `quire watch`
reruns only what changed.

```python
from quire import cache


@cache
def simulate(size, temperature, sweeps):
    return ising.run(size, temperature, sweeps)
```

A result is stored in `.quire-cache/` beside the article, keyed by the
function's arguments and its source. For a function defined in a fence, the
source is its own lines; for a function imported from a module, it is the whole
module file. Globals the function reads and helpers in other modules are not
part of the key: pass a value as an argument, or build with `--no-cache` to run
every function again. Arguments and results must pickle. Outside a quire build,
a cached function runs as usual.

## Publish

Add the article to the catalog with its `.md` file, as in
[notebooks](notebooks.md#catalog-entries), and add `quire` to the package's
dependencies with `{ workspace = true }` in `[tool.uv.sources]`. The export
command builds every article in the catalog into `site/.articles`, and the site
prerenders one page per article at `/notebooks/<topic>/<notebook>/`.
