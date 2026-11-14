import * as Plot from "@observablehq/plot";

import type { MarkSpec, PlotSpec } from "./types.js";

type MarkFactory = (
  data: unknown,
  options: Record<string, unknown>,
) => Plot.Markish;

/** Marks whose `series` color is their fill; every other mark colors its stroke. */
const FILLED = new Set([
  "area",
  "areaX",
  "areaY",
  "barX",
  "barY",
  "cell",
  "dot",
  "rect",
]);
const TIPPED = new Set([
  "line",
  "dot",
  "areaY",
  "area",
  "barY",
  "barX",
  "cell",
]);
const X_CHANNELS = ["x", "x1", "x2"];
const Y_CHANNELS = ["y", "y1", "y2"];

export function renderPlot(
  spec: PlotSpec,
  frame: number,
  width: number,
  palette: string[],
): SVGSVGElement | HTMLElement {
  const options: Record<string, unknown> = { ...spec.options };
  options.x = withLogTicks(options.x);
  options.y = withLogTicks(options.y);
  if (spec.frames) {
    // Fixed scales, or the axes would jump from frame to frame.
    options.x = withDomain(options.x, spec.marks, X_CHANNELS);
    options.y = withDomain(options.y, spec.marks, Y_CHANNELS);
  }
  if (palette.length > 0 && usesCategoricalColor(spec)) {
    // Named series need a key; a figure with none keeps the legend off.
    const legend = spec.marks.some((mark) => mark.series !== undefined);
    const domain = seriesOrder(spec.marks);
    options.color = {
      range: palette,
      domain,
      legend,
      ...(options.color as object),
    };
  }
  return Plot.plot({
    ...options,
    width,
    marks: spec.marks.map((mark) => buildMark(mark, frame)),
    style: {
      background: "transparent",
      color: "var(--content)",
      fontFamily: "var(--font-mono)",
      fontSize: "12px",
      overflow: "visible",
    },
  });
}

function buildMark(mark: MarkSpec, frame: number): Plot.Markish {
  const channels: Record<string, unknown[]> = { ...mark.channels };
  for (const [name, frames] of Object.entries(mark.animated ?? {}))
    channels[name] = frames[frame];

  const options: Record<string, unknown> = { ...mark.options, ...channels };
  if (mark.series !== undefined) {
    const series = mark.series;
    // An empty label makes the tip show the series name beside its swatch.
    options[FILLED.has(mark.kind) ? "fill" : "stroke"] = {
      value: () => series,
      label: "",
    };
  }
  // z repeats the series a line or area groups by.
  if (TIPPED.has(mark.kind) && !("tip" in options))
    options.tip = { format: { z: false } };

  const length = Object.values(channels)[0]?.length ?? 0;
  const factory = (Plot as unknown as Record<string, MarkFactory>)[mark.kind];
  if (typeof factory !== "function")
    throw new Error(`Unknown Plot mark: ${mark.kind}`);
  return factory(mark.data ?? { length }, options);
}

const SUPERSCRIPT: Record<string, string> = {
  "-": "⁻",
  "0": "⁰",
  "1": "¹",
  "2": "²",
  "3": "³",
  "4": "⁴",
  "5": "⁵",
  "6": "⁶",
  "7": "⁷",
  "8": "⁸",
  "9": "⁹",
};

/** Labels a decade as 10ⁿ; any other value keeps a short general format. */
function powerOfTen(value: number): string {
  const exponent = Math.log10(value);
  if (!Number.isInteger(exponent)) return value.toPrecision(2);
  if (exponent >= 0 && exponent <= 3) return String(value);
  return `10${[...String(exponent)].map((c) => SUPERSCRIPT[c]).join("")}`;
}

/**
 * A log axis gets few ticks, so d3 keeps whole decades only, and labels them
 * as powers of ten instead of SI prefixes such as "100m".
 */
function withLogTicks(scale: unknown): unknown {
  const options = (scale ?? {}) as Record<string, unknown>;
  if (options.type !== "log") return scale;
  return { ticks: 4, tickFormat: powerOfTen, ...options };
}

function withDomain(
  scale: unknown,
  marks: MarkSpec[],
  names: string[],
): unknown {
  const options = (scale ?? {}) as Record<string, unknown>;
  if (options.domain !== undefined) return options;

  let min = Infinity;
  let max = -Infinity;
  for (const mark of marks) {
    const values = names.flatMap((name) => [
      ...(mark.channels?.[name] ?? []),
      ...(mark.animated?.[name]?.flat() ?? []),
    ]);
    for (const value of values) {
      if (typeof value !== "number") continue;
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
  }
  return min <= max ? { ...options, domain: [min, max] } : options;
}

/** A theme palette only suits named series, not a continuous color channel. */
function usesCategoricalColor(spec: PlotSpec): boolean {
  const color = (spec.options.color ?? {}) as Record<string, unknown>;
  if (
    color.scheme !== undefined ||
    color.range !== undefined ||
    color.type !== undefined
  ) {
    return false;
  }
  return spec.marks.every((mark) =>
    ["fill", "stroke"].every((name) => {
      const values = mark.channels?.[name] ?? mark.animated?.[name]?.[0];
      return !values?.some((value) => typeof value === "number");
    }),
  );
}

/** Series names in the order the article wrote them; Plot would sort them. */
function seriesOrder(marks: MarkSpec[]): string[] {
  const names = new Set<string>();
  for (const mark of marks) {
    if (mark.series !== undefined) names.add(mark.series);
    for (const channel of ["fill", "stroke"]) {
      const values =
        mark.channels?.[channel] ?? mark.animated?.[channel]?.[0] ?? [];
      for (const value of values)
        if (typeof value === "string") names.add(value);
    }
  }
  return [...names];
}

export function readPalette(element: Element): string[] {
  const style = getComputedStyle(element);
  const colors: string[] = [];
  for (let i = 1; ; i++) {
    const color = style.getPropertyValue(`--chart-${i}`).trim();
    if (!color) return colors;
    colors.push(color);
  }
}
