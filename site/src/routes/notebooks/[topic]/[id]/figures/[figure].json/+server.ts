import { error, json } from "@sveltejs/kit";

import { topics } from "#lib/catalog.generated.js";
import { lazyFigures, loadFigure } from "#lib/server/article.js";

import type { EntryGenerator, RequestHandler } from "./$types";

// A `+server` route does not inherit `prerender` from the root layout.
export const prerender = true;

export const entries: EntryGenerator = async () => {
  const slugs = topics.flatMap((topic) =>
    topic.notebooks.map((notebook) => notebook.slug),
  );
  const perArticle = await Promise.all(
    slugs.map(async (slug) => {
      const [topic, id] = slug.split("/");
      return (await lazyFigures(slug)).map((figure) => ({
        topic,
        id,
        figure: String(figure),
      }));
    }),
  );
  return perArticle.flat();
};

export const GET: RequestHandler = async ({ params }) => {
  const index = Number(params.figure);
  const figure = Number.isInteger(index)
    ? await loadFigure(`${params.topic}/${params.id}`, index)
    : undefined;
  if (!figure) error(404, "No such figure");
  return json(figure);
};
