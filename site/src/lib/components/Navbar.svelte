<script lang="ts">
	import { resolve } from '$app/paths';
	import type { Snippet } from 'svelte';

	let {
		title,
		section,
		children
	}: { title: string; section?: { title: string; href: string }; children?: Snippet } = $props();
</script>

<header class="topbar">
	<div class="topbar__inner" class:topbar__inner--wrap={!section}>
		<p class="topbar__trail">
			<a class="topbar__brand" href={resolve('/')}>{title}</a>
			{#if section}
				<span class="topbar__slash" aria-hidden="true">/</span>
				<a class="topbar__section" href={section.href}>{section.title.toLowerCase()}</a>
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
		align-items: baseline;
		gap: 0.5rem;
		min-width: 0;
		margin: 0;
		font-size: var(--text-title);
	}
	.topbar__brand {
		flex-shrink: 0;
		font-weight: 700;
		color: var(--content);
	}
	.topbar__slash {
		color: var(--content-secondary);
	}
	.topbar__section {
		overflow: hidden;
		color: var(--content-secondary);
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.topbar__brand:hover,
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
	}
</style>
