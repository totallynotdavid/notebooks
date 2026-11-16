export type Zoom = { x?: unknown[]; y?: unknown[] };

type Scale = {
  type: string;
  domain: unknown[];
  range: number[];
  invert?: (pixel: number) => unknown;
};
type Chart = (SVGSVGElement | HTMLElement) & {
  scale?: (name: string) => Scale | undefined;
};

const CONTINUOUS = new Set([
  "linear",
  "log",
  "pow",
  "sqrt",
  "symlog",
  "time",
  "utc",
]);
/** A drag shorter than this, in pixels, is a click and keeps the scale. */
const MIN_DRAG = 6;
const SVG = "http://www.w3.org/2000/svg";

/**
 * Lets the reader drag a box over a chart to zoom into it. Only continuous
 * scales zoom; a band or ordinal axis keeps its domain. Returns a cleanup.
 */
export function attachZoom(
  chart: Chart,
  onZoom: (zoom: Zoom) => void,
): () => void {
  const x = zoomable(chart.scale?.("x"));
  const y = zoomable(chart.scale?.("y"));
  // A figure with a title or legend wraps the chart; the chart is its last svg.
  const svg =
    chart instanceof SVGSVGElement
      ? chart
      : [...chart.querySelectorAll(":scope > svg")].at(-1);
  if ((!x && !y) || !(svg instanceof SVGSVGElement)) return () => {};

  svg.style.cursor = "crosshair";
  let start: [number, number] | undefined;
  let box: SVGRectElement | undefined;

  // Plot draws in its own pixel units; CSS may shrink the svg below them.
  const point = (event: PointerEvent): [number, number] => {
    const rect = svg.getBoundingClientRect();
    const unit = svg.width.baseVal.value / rect.width;
    return [
      (event.clientX - rect.left) * unit,
      (event.clientY - rect.top) * unit,
    ];
  };
  // An axis that does not zoom keeps the box across its whole range.
  const fullX = sorted(
    chart.scale?.("x")?.range ?? [0, svg.width.baseVal.value],
  );
  const fullY = sorted(
    chart.scale?.("y")?.range ?? [0, svg.height.baseVal.value],
  );

  const down = (event: PointerEvent) => {
    if (event.button !== 0) return;
    start = point(event);
    box = document.createElementNS(SVG, "rect");
    box.setAttribute("fill", "currentColor");
    box.setAttribute("fill-opacity", "0.08");
    box.setAttribute("stroke", "currentColor");
    box.setAttribute("stroke-dasharray", "3 3");
    box.setAttribute("pointer-events", "none");
    svg.append(box);
    svg.setPointerCapture(event.pointerId);
  };
  const move = (event: PointerEvent) => {
    if (!start || !box) return;
    const [px, py] = point(event);
    const [x0, x1] = x ? span(start[0], px) : fullX;
    const [y0, y1] = y ? span(start[1], py) : fullY;
    box.setAttribute("x", String(x0));
    box.setAttribute("y", String(y0));
    box.setAttribute("width", String(x1 - x0));
    box.setAttribute("height", String(y1 - y0));
  };
  const up = (event: PointerEvent) => {
    if (!start) return;
    const [px, py] = point(event);
    const zoom: Zoom = {};
    if (x && Math.abs(px - start[0]) >= MIN_DRAG)
      zoom.x = domain(x, start[0], px);
    if (y && Math.abs(py - start[1]) >= MIN_DRAG)
      zoom.y = domain(y, start[1], py);
    cancel();
    if (zoom.x || zoom.y) onZoom(zoom);
  };
  const cancel = () => {
    start = undefined;
    box?.remove();
    box = undefined;
  };

  svg.addEventListener("pointerdown", down);
  svg.addEventListener("pointermove", move);
  svg.addEventListener("pointerup", up);
  svg.addEventListener("pointercancel", cancel);
  return () => {
    svg.removeEventListener("pointerdown", down);
    svg.removeEventListener("pointermove", move);
    svg.removeEventListener("pointerup", up);
    svg.removeEventListener("pointercancel", cancel);
  };
}

function zoomable(scale: Scale | undefined): Scale | undefined {
  return scale && CONTINUOUS.has(scale.type) && scale.invert
    ? scale
    : undefined;
}

function span(a: number, b: number): [number, number] {
  return a < b ? [a, b] : [b, a];
}

function sorted(range: number[]): [number, number] {
  return span(range[0], range[range.length - 1]);
}

/** The values under two pixels, in the direction the scale already runs. */
function domain(scale: Scale, a: number, b: number): unknown[] {
  const values = [scale.invert!(a), scale.invert!(b)];
  const ascending =
    +(scale.domain[0] as number) <= +(scale.domain.at(-1) as number);
  return values.toSorted(
    (p, q) => (ascending ? 1 : -1) * (+(p as number) - +(q as number)),
  );
}
