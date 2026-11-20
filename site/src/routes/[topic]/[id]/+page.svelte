<script lang="ts">
	import 'katex/dist/katex.min.css';
	import '#lib/article/prose.css';

	import { resolve } from '$app/paths';

	import Navbar from '#lib/components/Navbar.svelte';
	import CodeBlock from '#lib/components/article/CodeBlock.svelte';
	import CodeToggle from '#lib/components/article/CodeToggle.svelte';
	import LazyFigure from '#lib/components/article/LazyFigure.svelte';
	import Output from '#lib/components/article/Output.svelte';
	import { site } from '#lib/catalog.generated.js';
	import { attachValues, PageParameters, setParameters } from '#lib/article/parameters.svelte.js';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const page = setParameters(new PageParameters(() => data));

	const hasCode = $derived(data.blocks.some((block) => block.type !== 'html' && block.html));

	const figureUrl = (figure: number) => {
		const [topic, id] = data.notebook.slug.split('/');
		return resolve('/[topic]/[id]/figures/[figure].json', {
			topic,
			id,
			figure: String(figure)
		});
	};
</script>

<svelte:head>
	<title>{data.notebook.title} · {site.title}</title>
	<meta name="description" content={data.notebook.summary} />
</svelte:head>

<Navbar
	title={site.title}
	section={{ title: data.topic.title, href: `${resolve('/')}?topic=${data.topic.id}` }}
>
	{#if hasCode}
		<CodeToggle />
	{/if}
</Navbar>

<!-- A new article is a new tree: the values attach to its own prose. -->
{#key data.notebook.slug}
<main class="article" lang="es" {@attach attachValues(page)}>
	{#each data.blocks as block, i (i)}
		{#if block.type === 'html'}
			<!-- Rendered at build time from the article's own Markdown. -->
			<div class="prose">{@html block.html}</div>
		{:else}
			{#if block.html}
				<CodeBlock html={block.html} />
			{/if}
			{#each block.outputs as output, j (j)}
				{#if output.type === 'lazy'}
					<LazyFigure lazy={output} src={figureUrl(output.figure)} />
				{:else}
					<Output {output} />
				{/if}
			{/each}
		{/if}
	{/each}
	<footer class="source" lang="en">
		<a href={data.notebook.sourceUrl}>Article source on GitHub</a>
		<a href={resolve('/')}>All notebooks</a>
	</footer>
</main>
{/key}

<style>
	.article {
		--content-width: 40rem;
		--wide-width: 64rem;
		/* Grid items keep both margins, so the top adds to the paragraph's 1rem. */
		--figure-margin: 1.5rem 0 2.5rem;

		display: grid;
		grid-template-columns:
			[full-start] minmax(var(--gutter), 1fr)
			[wide-start] minmax(0, calc((var(--wide-width) - var(--content-width)) / 2))
			[content-start] min(var(--content-width), 100% - 2 * var(--gutter))
			[content-end] minmax(0, calc((var(--wide-width) - var(--content-width)) / 2))
			[wide-end] minmax(var(--gutter), 1fr) [full-end];
		padding: 2.5rem 0 4rem;
	}
	.article > :global(*) {
		grid-column: content;
	}
	.article > :global(.wide) {
		grid-column: wide;
	}
	.source {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.5rem;
		margin-top: 2rem;
		padding-top: 1.25rem;
		border-top: 1px solid var(--line);
		font-family: var(--font-mono);
		font-size: var(--text-label);
	}

</style>
