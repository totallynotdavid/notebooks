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
shows only its outputs. The site hides all code until the reader presses "Show
code" in the header, and remembers that choice across articles. The prose must
read without the code.

A fence has up to two outputs: what it printed, then the value of its last
expression. A value of `None` shows nothing. The value becomes:

| Value                 | Output                                                                        |
| --------------------- | ----------------------------------------------------------------------------- |
| `md(text)`            | Markdown and math, so an f-string puts computed numbers into prose and tables |
| `table(header, rows)` | A Markdown table built from computed rows                                     |
| `P.figure(...)`       | A chart drawn in the browser                                                  |
| `P.grid(figure, ...)` | Charts side by side, one column on a narrow page                              |
| anything else         | Its `repr` as plain text                                                      |

`md` removes the common indentation of its text.

## Math and tables on a phone

The article column is about 21rem wide on a phone, and nothing in it scales down
to fit.

- Write a display formula that fits that width. Stack equations with `aligned`
  on `=` or with `gathered`, and give a long term a name defined on its own
  line. KaTeX breaks inline math only after a relation or an operator, so write
  a list of values as separate inline formulas: `$y=0.671$, $0.620$`.
- A right-aligned column (`---:`) holds numbers. It is set in mono and stays on
  one line. Any other column wraps between words. `table` right-aligns every
  column after the first whose cells are all numbers.
- A table still wider than the column scrolls sideways with its first column
  pinned. Drop or split columns before relying on that.

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

A figure sends only the points a reader can see. A `line` with numeric `x` and
`y` keeps the vertices that move it by more than half a pixel of an 800 px
figure, measured on the axis `domain` and `type`, so a log axis thins in log
space. Each `z` group, or each `stroke` or `fill` value when `z` is absent,
thins as its own line. A `dot` with only `x` and `y` channels and no opacity
keeps one dot per half-pixel cell. Animated channels and `since` marks are sent
whole. [`quire.thin`](../lib/quire/src/quire/thin.py) does the thinning, so a
long integration can go to `P.line` as it is.

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

When the frames are values of a parameter rather than steps in time, pass the
parameter as `frames`; see [Parameters](#parameters).

A channel whose element count changes between frames is padded with NaN to the
longest frame; Plot skips the NaN points.

Elements that accumulate, such as the iterates of a method, are sent once with a
`since` channel that holds the frame each element first appears in:

```python
P.dot(x=iterados, y=np.zeros(n), since=np.arange(n))
```

An axis `domain` with one `[min, max]` row per frame zooms that axis with the
frame. Use it to follow a value that converges into a window too small to see at
the first frame's scale:

```python
x = {"domain": [[c - w, c + w] for c, w in zip(centros, semianchos)]}
```

Every frame is stored in the article, so keep frames few and rounded. A figure
larger than 16 KB loads from its own file as it nears the view; see
[architecture.md](architecture.md).

## Parameters

`quire.parameter` makes a number the reader drags. Put it in an `md` f-string
and it shows as an underlined value inside the prose or the math; the reader
drags it sideways, or focuses it and uses the arrow keys, Page Up, Page Down,
Home and End. `each` gives a value per parameter value that follows the drag. A
figure with the parameter as `frames` shows the frame of the current value, with
a slider under it instead of play.

```python
grado = parameter("n", grados, value=14, format="{}")

md(f"""
Con $n = {grado}$ el error máximo es {grado.each(errores):.2g}.
""")

P.figure(
    P.line(x=malla, y=curvas),  # curvas has shape (len(grados), len(malla))
    frames=grado,
)
```

`values` is the list of values, and `value` is the one the page starts at.
`format` writes each value's label, which the prose and the figure's slider
show; a format spec in the f-string, as in `{grado:.1f}`, replaces it in that
sentence. `each` takes a function of the value or a list with one item per
value. A value's text cannot hold `{`, `}`, `\` or `$`.

Every value and figure of one parameter moves together across the article. While
the reader drags, the values that follow it turn to the accent color, and each
animated `line` keeps a dashed copy of where the drag started.

Every value's text is stored for every parameter value, like a figure's frames.
Keep the values few.

## Formula notes

`\note{label}{term}` in display math colors the term and writes the label under
the formula in the same color. Pointing at a term or its label dims the other
notes. The label is Markdown and may hold math.

```markdown
$$
T = \note{$T_0$ dividido entre $\pi/2$}{\frac{4}{\omega_0}} K(m)
$$
```

A formula holds at most 6 notes, one per chart color. Math renders with KaTeX at
build time, and an error in any formula fails the build.

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
function's arguments, its own source, and every `.py` file in the article's
package outside `tests/`. Editing a module the article imports therefore runs
the function again; editing prose does not. Globals the function reads and
installed libraries are not part of the key: pass a value as an argument, or
build with `--no-cache` to run every function again. Arguments and results must
pickle. Outside a quire build, a cached function runs as usual.

## Publish

Add the article to the catalog with its `.md` file, as in
[notebooks](notebooks.md#catalog-entries), and add `quire` to the package's
dependencies with `{ workspace = true }` in `[tool.uv.sources]`. The export
command builds every article in the catalog into `site/.articles`, and the site
prerenders one page per article at `/notebooks/<topic>/<notebook>/`.
