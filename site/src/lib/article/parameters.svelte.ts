import { createContext } from "svelte";
import type { Attachment } from "svelte/attachments";

import type { Article, ParameterSpec, ValueSpec } from "./types.js";

/** The value each of an article's parameters shows, shared by its prose and figures. */
export class PageParameters {
  readonly #source: () => Pick<Article, "parameters" | "values">;
  /** The index of each parameter's current value; a new article resets it. */
  current: number[] = $derived(this.specs.map((spec) => spec.start));
  /** The value a drag started from, per parameter; null when nobody drags. */
  held: (number | null)[] = $derived(this.specs.map(() => null));

  constructor(source: () => Pick<Article, "parameters" | "values">) {
    this.#source = source;
  }

  get specs(): ParameterSpec[] {
    return this.#source().parameters;
  }

  get values(): ValueSpec[] {
    return this.#source().values;
  }

  set(parameter: number, index: number): void {
    const last = this.specs[parameter].labels.length - 1;
    const next = Math.min(last, Math.max(0, Math.round(index)));
    if (next !== this.current[parameter])
      this.current = this.current.with(parameter, next);
  }

  hold(parameter: number): void {
    this.held = this.held.with(parameter, this.current[parameter]);
  }

  release(parameter: number): void {
    this.held = this.held.with(parameter, null);
  }
}

export const [getParameters, setParameters] = createContext<PageParameters>();

/** A full drag across a parameter's values, in pixels, within the step bounds. */
const DRAG_WIDTH = 240;
const MIN_STEP = 6;
const MAX_STEP = 24;

/**
 * Turns every `[data-qv]` span the Markdown renderer wrote under `root` into
 * text that follows its parameter, and the parameter's own spans into
 * horizontal sliders: drag, or focus and use the arrow keys.
 */
export function attachValues(page: PageParameters): Attachment<HTMLElement> {
  return (root) => {
    for (const element of root.querySelectorAll<HTMLElement>("[data-qv]")) {
      const value = page.values[Number(element.dataset.qv)];
      if (!value)
        throw new Error(`No value ${element.dataset.qv} on this page`);
      follow(element, value, page);
      if (value.input) slider(element, value.parameter, page);
    }
  };
}

function follow(element: HTMLElement, value: ValueSpec, page: PageParameters) {
  const p = value.parameter;
  element.classList.add("qv");
  // The widest text keeps its place, so the line does not reflow on a drag.
  void document.fonts.ready.then(() => {
    element.style.minWidth = `${Math.ceil(widest(element, value.text))}px`;
  });
  $effect(() => {
    element.textContent = value.text[page.current[p]];
    element.classList.toggle("qv--held", page.held[p] !== null);
  });
}

let measure: CanvasRenderingContext2D | null = null;

/** The width of the widest text in the element's own font. */
function widest(element: HTMLElement, texts: string[]): number {
  measure ??= document.createElement("canvas").getContext("2d");
  if (!measure) return 0;
  // The `font` shorthand reads empty when tabular-nums is set, so build it.
  const style = getComputedStyle(element);
  measure.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
  return Math.max(...texts.map((text) => measure!.measureText(text).width));
}

function slider(element: HTMLElement, p: number, page: PageParameters) {
  const spec = page.specs[p];
  const last = spec.labels.length - 1;
  const step = Math.min(MAX_STEP, Math.max(MIN_STEP, DRAG_WIDTH / last));
  element.classList.add("qv--input");
  element.tabIndex = 0;
  element.setAttribute("role", "slider");
  element.setAttribute("aria-label", spec.name);
  element.setAttribute("aria-valuemin", "0");
  element.setAttribute("aria-valuemax", String(last));

  $effect(() => {
    element.setAttribute("aria-valuenow", String(page.current[p]));
    element.setAttribute("aria-valuetext", spec.labels[page.current[p]]);
  });

  $effect(() => {
    let from = 0;
    let x = 0;
    const controller = new AbortController();
    const options = { signal: controller.signal };
    element.addEventListener(
      "pointerdown",
      (event) => {
        if (event.button !== 0) return;
        // Keeps the browser from selecting text while the pointer moves.
        event.preventDefault();
        element.setPointerCapture(event.pointerId);
        element.focus({ preventScroll: true });
        from = page.current[p];
        x = event.clientX;
        page.hold(p);
      },
      options,
    );
    element.addEventListener(
      "pointermove",
      (event) => {
        if (!element.hasPointerCapture(event.pointerId)) return;
        page.set(p, from + (event.clientX - x) / step);
      },
      options,
    );
    for (const type of ["pointerup", "pointercancel"])
      element.addEventListener(type, () => page.release(p), options);
    element.addEventListener(
      "keydown",
      (event) => {
        const page_step = Math.max(1, Math.round(last / 10));
        const moves: Record<string, number> = {
          ArrowRight: page.current[p] + 1,
          ArrowUp: page.current[p] + 1,
          ArrowLeft: page.current[p] - 1,
          ArrowDown: page.current[p] - 1,
          PageUp: page.current[p] + page_step,
          PageDown: page.current[p] - page_step,
          Home: 0,
          End: last,
        };
        if (!(event.key in moves)) return;
        event.preventDefault();
        page.set(p, moves[event.key]);
      },
      options,
    );
    return () => controller.abort();
  });
}
