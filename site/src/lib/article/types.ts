// The document `quire build` writes (lib/quire), and the page data the route
// derives from it.

export interface MarkSpec {
  kind: string;
  options: Record<string, unknown>;
  data?: unknown[];
  /** Arrays drawn once, one value per element. */
  channels?: Record<string, unknown[]>;
  /** One array per frame. */
  animated?: Record<string, unknown[][]>;
  /** Names the mark in the color legend. */
  series?: string;
}

export interface PlotSpec {
  type: "plot";
  marks: MarkSpec[];
  options: Record<string, unknown>;
  frames?: { labels: string[]; fps: number };
}

export interface GridSpec {
  type: "grid";
  figures: PlotSpec[];
}

export type FigureSpec = PlotSpec | GridSpec;

export type QuireOutput =
  | { type: "markdown"; text: string }
  | { type: "text" | "stdout"; text: string }
  | FigureSpec;

export type QuireBlock =
  | { type: "prose"; text: string }
  | { type: "code"; source: string; hidden: boolean; outputs: QuireOutput[] };

export interface QuireDocument {
  version: 1;
  blocks: QuireBlock[];
}

/** A large figure the page fetches from `figures/{figure}.json` near the view. */
export interface LazyFigure {
  type: "lazy";
  figure: number;
  /** Pixels to reserve until the figure draws. */
  height: number;
}

export type Output =
  | { type: "html"; html: string }
  | { type: "text"; text: string }
  | FigureSpec
  | LazyFigure;

export type Block =
  | { type: "html"; html: string }
  | { type: "code"; html: string | null; outputs: Output[] };
