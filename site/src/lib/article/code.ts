/**
 * Whether article code is shown. The choice lives on <html> as `data-code`, so
 * CSS hides every code block at once, and in localStorage so it survives a
 * reload. app.html reads the same key before the first paint.
 */
const KEY = "notebooks:code";

export function codeShown(): boolean {
  return document.documentElement.hasAttribute("data-code");
}

export function showCode(shown: boolean): void {
  document.documentElement.toggleAttribute("data-code", shown);
  try {
    if (shown) localStorage.setItem(KEY, "shown");
    else localStorage.removeItem(KEY);
  } catch {
    // Storage can be off in private windows; the choice then lasts the page.
  }
}
