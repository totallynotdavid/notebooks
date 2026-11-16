<script lang="ts">
	import { untrack } from 'svelte';

	import type { Output } from '#lib/article/types.js';

	import Player from './Player.svelte';
	import PlotFigure from './PlotFigure.svelte';

	let { output }: { output: Exclude<Output, { type: 'lazy' }> } = $props();

	// Animated figures in one grid move together under the first one's player.
	const shared = $derived(
		output.type === 'grid' && output.figures.every((figure) => figure.frames)
			? output.figures[0].frames
			: undefined
	);
	// The player owns the frame after the first render.
	let frame = $state(untrack(() => shared?.start ?? 0));
</script>

{#if output.type === 'html'}
	<!-- Rendered at build time from the article's own Markdown. -->
	<div class="prose">{@html output.html}</div>
{:else if output.type === 'text'}
	<pre class="text">{output.text}</pre>
{:else if output.type === 'plot'}
	<figure class="wide"><PlotFigure spec={output} /></figure>
{:else if output.type === 'grid'}
	<figure class="wide">
		<div class="grid">
			{#each output.figures as figure, i (i)}
				{#if shared}
					<PlotFigure spec={figure} {frame} player={false} />
				{:else}
					<PlotFigure spec={figure} />
				{/if}
			{/each}
		</div>
		{#if shared}
			<Player frames={shared} bind:frame />
		{/if}
	</figure>
{/if}

<style>
	figure {
		margin: var(--figure-margin);
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
		gap: 2rem;
	}
	.text {
		overflow-x: auto;
		padding: 0.75rem 1rem;
		background: var(--code-bg);
		border-radius: var(--radius);
		font: var(--text-label) / 1.5 var(--font-mono);
	}
</style>
