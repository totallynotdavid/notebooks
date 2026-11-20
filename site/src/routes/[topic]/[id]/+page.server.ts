import { error } from "@sveltejs/kit";

import { topics } from "#lib/catalog.generated.js";
import { loadArticle } from "#lib/server/article.js";

import type { EntryGenerator, PageServerLoad } from "./$types";

const articles = topics.flatMap((topic) =>
  topic.notebooks.map((notebook) => ({ topic, notebook })),
);

export const trailingSlash = "always";

export const entries: EntryGenerator = () =>
  articles.map(({ notebook }) => {
    const [topic, id] = notebook.slug.split("/");
    return { topic, id };
  });

export const load: PageServerLoad = async ({ params }) => {
  const slug = `${params.topic}/${params.id}`;
  const entry = articles.find(({ notebook }) => notebook.slug === slug);
  if (!entry) error(404, `No article ${slug}`);
  return {
    topic: { id: entry.topic.id, title: entry.topic.title },
    notebook: entry.notebook,
    ...(await loadArticle(slug)),
  };
};
