import katexPluginModule from "@vscode/markdown-it-katex";
import katex, { type KatexOptions } from "katex";
import type { MarkdownIt, RendererRule, StateInline } from "markdown-it";

// The package is CommonJS with an `__esModule` default. Node's ESM loader hands
// back the whole `module.exports`, while the types promise the plugin itself.
const katexPlugin =
  (katexPluginModule as unknown as { default?: typeof katexPluginModule })
    .default ?? katexPluginModule;

/** Colors a note can take: the six `--chart-*` colors; see prose.css. */
export const MAX_NOTES = 6;

const OPTIONS: KatexOptions = {
  throwOnError: true,
  // A value written by `quire.parameter`, see lib/quire/src/quire/parameter.py.
  macros: { "\\qv": "\\htmlData{qv=#1}{\\text{#2}}" },
  trust: (context) => context.command === "\\htmlData",
  strict: (code: string) => (code === "htmlExtension" ? "ignore" : "error"),
};

function render(latex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(latex, { ...OPTIONS, displayMode });
  } catch (error) {
    throw new Error(`KaTeX cannot render ${JSON.stringify(latex)}: ${error}`, {
      cause: error,
    });
  }
}

/** The text of the brace group that opens at `start`, and the index after it. */
function group(latex: string, start: number): [string, number] {
  if (latex[start] !== "{")
    throw new Error(`\\note needs two {groups} in ${JSON.stringify(latex)}`);
  let depth = 0;
  for (let i = start; i < latex.length; i++) {
    if (latex[i] === "\\") i++;
    else if (latex[i] === "{") depth++;
    else if (latex[i] === "}" && --depth === 0)
      return [latex.slice(start + 1, i), i + 1];
  }
  throw new Error(`Unbalanced braces in ${JSON.stringify(latex)}`);
}

/**
 * `\note{label}{tex}` in display math: the term takes note i's color, and
 * the label goes under the formula in the same color.
 */
export function extractNotes(latex: string): {
  latex: string;
  notes: string[];
} {
  const notes: string[] = [];
  let out = "";
  let at = 0;
  for (let found = latex.indexOf("\\note{"); found !== -1;) {
    const [label, afterLabel] = group(latex, found + "\\note".length);
    const [term, end] = group(latex, afterLabel);
    notes.push(label);
    out += `${latex.slice(at, found)}\\htmlData{note=${notes.length}}{${term}}`;
    at = end;
    found = latex.indexOf("\\note{", at);
  }
  if (notes.length > MAX_NOTES)
    throw new Error(`More than ${MAX_NOTES} notes in ${JSON.stringify(latex)}`);
  return { latex: out + latex.slice(at), notes };
}

/** `\qv{k}{text}` in prose: value k of the page's parameters, see parameters.svelte.ts. */
function value(state: StateInline, silent: boolean): boolean {
  const match = /^\\qv\{(\d+)\}\{([^{}\\$]*)\}/.exec(
    state.src.slice(state.pos),
  );
  if (!match) return false;
  if (!silent) {
    const token = state.push("quire_value", "span", 0);
    token.meta = { index: match[1], text: match[2] };
  }
  state.pos += match[0].length;
  return true;
}

/** Math through KaTeX, with notes in display math and draggable values. */
export function math(md: MarkdownIt): void {
  md.use(katexPlugin);
  md.inline.ruler.before("escape", "quire_value", value);

  md.renderer.rules.quire_value = (tokens, idx) => {
    const { index, text } = tokens[idx].meta as { index: string; text: string };
    return `<span data-qv="${index}">${md.utils.escapeHtml(text)}</span>`;
  };
  md.renderer.rules.math_inline = (tokens, idx) =>
    render(tokens[idx].content, false);

  const block: RendererRule = (tokens, idx) => {
    const { latex, notes } = extractNotes(tokens[idx].content);
    const formula = `<p class="katex-block">${render(latex, true)}</p>`;
    if (notes.length === 0) return `${formula}\n`;
    const items = notes
      .map(
        (note, i) => `<li data-note="${i + 1}">${md.renderInline(note)}</li>`,
      )
      .join("");
    return `<div class="formula">${formula}<ol class="formula__notes">${items}</ol></div>\n`;
  };
  md.renderer.rules.math_block = block;
  md.renderer.rules.math_inline_block = block;
}
