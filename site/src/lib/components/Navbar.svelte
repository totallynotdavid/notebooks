<script lang="ts">
	import { resolve } from '$app/paths';
	import type { Snippet } from 'svelte';

	import Mark from '#lib/components/Mark.svelte';

	let {
		title,
		section,
		children
	}: { title: string; section?: { title: string; href: string }; children?: Snippet } = $props();
</script>

<header class="topbar">
	<div class="topbar__inner" class:topbar__inner--wrap={!section}>
		<p class="topbar__trail">
			<a class="topbar__brand" href={resolve('/')} aria-label={title}>
				<Mark />
				<span class="topbar__name">{title}</span>
			</a>
			{#if section}
				<a class="topbar__section" href={section.href}>{section.title}</a>
			{/if}
		</p>
		{#if children}
			<div class="topbar__controls">{@render children()}</div>
		{/if}
	</div>
</header>

<style>
	.topbar {
		position: sticky;
		top: 0;
		z-index: 200;
		background: var(--surface);
		border-bottom: 1px solid var(--line);
	}
	.topbar__inner {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem 1.25rem;
		min-height: var(--navbar-height);
		max-width: var(--layout-width);
		margin: 0 auto;
		padding: 0.7rem var(--gutter);
	}
	.topbar__trail {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		min-width: 0;
		margin: 0;
	}
	.topbar__brand {
		display: flex;
		flex-shrink: 0;
		align-items: center;
		gap: 0.5rem;
		font-size: 1.125rem;
		font-weight: 700;
		color: var(--content);
	}
	/* The section reads as a label after the brand, so the article's h1 stays
	   the only large serif line on the page. */
	.topbar__section {
		overflow: hidden;
		padding-left: 0.875rem;
		border-left: 1px solid var(--line);
		font-family: var(--font-mono);
		font-size: 0.8rem;
		line-height: 1.5rem;
		color: var(--content-secondary);
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.topbar__brand:hover .topbar__name,
	.topbar__section:hover {
		color: var(--content);
		text-decoration: underline;
	}
	.topbar__controls {
		flex: 0 1 auto;
		margin-left: auto;
		display: flex;
		min-width: 0;
	}

	/* The home page's search and filters take their own row on a phone. */
	@media (max-width: 640px) {
		:global(:root:has(.topbar__inner--wrap)) {
			--navbar-height: 6.75rem;
		}
		.topbar__inner--wrap .topbar__controls {
			flex-basis: 100%;
			margin-left: 0;
		}
		.topbar__inner:not(.topbar__inner--wrap) {
			flex-wrap: nowrap;
		}
		.topbar__inner:not(.topbar__inner--wrap) .topbar__controls {
			flex-shrink: 0;
		}
		/* On an article the mark alone links home, leaving the row to the section. */
		.topbar__inner:not(.topbar__inner--wrap) .topbar__name {
			display: none;
		}
	}
</style>
