import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import katexModule from "@vscode/markdown-it-katex";
import MarkdownIt from "markdown-it";
import { createHighlighter } from "shiki";

import type {
  Block,
  FigureSpec,
  Output,
  PlotSpec,
  QuireDocument,
  QuireOutput,
} from "#lib/article/types.js";

/** `quire build` writes one document per article here; see scripts/export_notebooks.py. */
const ARTICLES_DIR = resolve(".articles");

const highlighter = await createHighlighter({
  themes: ["github-light", "github-dark"],
  langs: ["python", "text", "sh"],
});

function highlight(code: string, lang: string): string {
  return highlighter.codeToHtml(code, {
    lang: highlighter.getLoadedLanguages().includes(lang) ? lang : "text",
    themes: { light: "github-light", dark: "github-dark" },
    defaultColor: false,
  });
}

// The package is CommonJS with an `__esModule` default. Node's ESM loader hands
// back the whole `module.exports`, while the types promise the plugin itself.
const katex =
  (katexModule as unknown as { default?: typeof katexModule }).default ??
  katexModule;

const markdown = new MarkdownIt({ highlight }).use(katex, {
  throwOnError: true,
});

/**
 * A figure whose JSON is larger than this leaves the page data and loads from
 * its own file when the reader scrolls near it. Smaller ones stay inline, so a
 * light chart never waits on a request.
 */
const INLINE_FIGURE_BYTES = 16_000;

const documents = new Map<string, Promise<QuireDocument>>();

function readDocument(slug: string): Promise<QuireDocument> {
  let document = documents.get(slug);
  if (!document) {
    document = readFile(resolve(ARTICLES_DIR, `${slug}.json`), "utf-8").then(
      (text) => {
        const parsed = JSON.parse(text) as QuireDocument;
        if (parsed.version !== 1)
          throw new Error(`${slug}: unknown document version`);
        return parsed;
      },
    );
    documents.set(slug, document);
  }
  return document;
}

/** The article's figures in document order; a figure's index is its file name. */
async function figures(slug: string): Promise<FigureSpec[]> {
  const document = await readDocument(slug);
  return document.blocks.flatMap((block) =>
    block.type === "code" ? block.outputs.filter(isFigure) : [],
  );
}

function isFigure(output: QuireOutput): output is FigureSpec {
  return output.type === "plot" || output.type === "grid";
}

function isLarge(figure: FigureSpec): boolean {
  return JSON.stringify(figure).length > INLINE_FIGURE_BYTES;
}

export async function loadArticle(slug: string): Promise<Block[]> {
  const document = await readDocument(slug);
  let index = 0;

  function renderOutput(output: QuireOutput): Output {
    switch (output.type) {
      case "markdown":
        return { type: "html", html: markdown.render(output.text) };
      case "text":
      case "stdout":
        return { type: "text", text: output.text };
      default: {
        const figure = index++;
        if (!isLarge(output)) return output;
        return { type: "lazy", figure, height: reservedHeight(output) };
      }
    }
  }

  return document.blocks.map((block): Block => {
    if (block.type === "prose")
      return { type: "html", html: markdown.render(block.text) };
    return {
      type: "code",
      html: block.hidden ? null : highlight(block.source, "python"),
      outputs: block.outputs.map(renderOutput),
    };
  });
}

/** Indexes of the figures that load from their own file. */
export async function lazyFigures(slug: string): Promise<number[]> {
  return (await figures(slug)).flatMap((figure, i) =>
    isLarge(figure) ? [i] : [],
  );
}

export async function loadFigure(
  slug: string,
  index: number,
): Promise<FigureSpec | undefined> {
  return (await figures(slug))[index];
}

// Pixel sizes measured on the rendered article, for the height estimate below.
const DEFAULT_PLOT_HEIGHT = 400;
const WIDE_WIDTH = 1024;
const GRID_GAP = 32;
const FIGURE_PADDING = 24;
const TITLE_HEIGHT = 40;
const LEGEND_HEIGHT = 50;
const PLAYER_HEIGHT = 48;

/**
 * Space a figure takes before its data arrives. The figure loads a screen
 * ahead of the reader, so an estimate keeps any shift out of view. A grid is
 * assumed to lay out two columns, as it does at the article's wide width.
 */
function reservedHeight(figure: FigureSpec): number {
  if (figure.type === "plot") return plotHeight(figure, WIDE_WIDTH);
  const rows = Math.ceil(figure.figures.length / 2);
  const column = (WIDE_WIDTH - GRID_GAP) / 2;
  const tallest = Math.max(
    ...figure.figures.map((plot) => plotHeight(plot, column)),
  );
  return rows * tallest + (rows - 1) * GRID_GAP;
}

function plotHeight(plot: PlotSpec, available: number): number {
  const { height, width, aspectRatio, title, color } = plot.options;
  // An aspect ratio sizes the chart from its width, close to square here.
  const chart =
    typeof height === "number"
      ? height
      : aspectRatio
        ? Math.min(typeof width === "number" ? width : available, available)
        : DEFAULT_PLOT_HEIGHT;
  const legend = (color as { legend?: boolean } | undefined)?.legend;
  return (
    chart +
    FIGURE_PADDING +
    (title ? TITLE_HEIGHT : 0) +
    (legend ? LEGEND_HEIGHT : 0) +
    (plot.frames ? PLAYER_HEIGHT : 0)
  );
}
