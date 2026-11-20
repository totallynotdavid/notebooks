import MarkdownIt from "markdown-it";
import { expect, test } from "vitest";

import { math } from "./math";

const md = new MarkdownIt().use(math);

/** Every value of `attribute` in the HTML, in order. */
const attributes = (html: string, attribute: string) =>
  [...html.matchAll(new RegExp(`${attribute}="([^"]*)"`, "g"))].map(
    (match) => match[1],
  );

test("a note colors its term and repeats it beside its label under the formula", () => {
  const html = md.render(
    "$$\nT = \\note{el período}{2\\pi} \\note{con $\\omega$}{/\\omega}\n$$\n",
  );
  const [formula, notes] = html.split('<ol class="formula__notes">');
  expect(formula).toMatch(/^<div class="formula"><p class="katex-block">/);
  expect(attributes(formula, "data-note")).toEqual(["1", "2"]);
  expect(attributes(notes, "data-note")).toEqual(["1", "2"]);
  expect(notes).toMatch(
    /<li><span class="formula__term" data-note="1"><span class="katex">.*π.*<\/span><span>el período<\/span><\/li>/,
  );
  expect(notes).toMatch(/<span>con <span class="katex">/);
});

test("inline math keeps the punctuation that closes it on its line", () => {
  const html = md.render("Si $x > 0$, entonces $y$; y $z$ no.\n");
  expect(html).toMatch(
    /<span class="nowrap"><span class="katex">.*?<\/span>,<\/span> entonces/,
  );
  expect(html).toMatch(
    /<span class="nowrap"><span class="katex">.*?<\/span>;<\/span> y <span class="katex">/,
  );
});

test("a formula without notes stays a plain block", () => {
  const html = md.render("$$\nx^2\n$$\n");
  expect(html).toMatch(/^<p class="katex-block"><span class="katex-display">/);
  expect(html).not.toContain("formula");
});

test("a value in prose and in math names its entry and shows its text", () => {
  const html = md.render("Con $n = \\qv{0}{14}$ el error es \\qv{1}{0.5}.\n");
  expect(attributes(html, "data-qv")).toEqual(["0", "1"]);
  expect(html).toMatch(/data-qv="0"[^>]*>.*14.*<\/span>/);
  expect(html).toContain('<span data-qv="1">0.5</span>');
});

test.each([
  ["seven notes", `$$\n${"\\note{a}{x}".repeat(7)}\n$$\n`, /More than 6 notes/],
  ["a note with one group", "$$\n\\note{a} x\n$$\n", /two \{groups\}/],
  ["an unknown command", "$\\nocommand$\n", /KaTeX cannot render/],
])("%s fails the build", (_, source, error) => {
  expect(() => md.render(source)).toThrow(error);
});
