import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import katexModule from "@vscode/markdown-it-katex";
import MarkdownIt from "markdown-it";
import { createHighlighter } from "shiki";

import type {
  Block,
  Output,
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

export async function loadArticle(slug: string): Promise<Block[]> {
  const path = resolve(ARTICLES_DIR, `${slug}.json`);
  const document = JSON.parse(await readFile(path, "utf-8")) as QuireDocument;
  if (document.version !== 1)
    throw new Error(`${path}: unknown document version`);

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

function renderOutput(output: QuireOutput): Output {
  switch (output.type) {
    case "markdown":
      return { type: "html", html: markdown.render(output.text) };
    case "text":
    case "stdout":
      return { type: "text", text: output.text };
    default:
      return output;
  }
}
