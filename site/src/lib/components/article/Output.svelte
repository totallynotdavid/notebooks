<script lang="ts">
	import type { Output } from '#lib/article/types.js';

	import PlotFigure from './PlotFigure.svelte';

	let { output }: { output: Output } = $props();
</script>

{#if output.type === 'html'}
	<!-- Rendered at build time from the article's own Markdown. -->
	<div class="prose">{@html output.html}</div>
{:else if output.type === 'text'}
	<pre class="text">{output.text}</pre>
{:else if output.type === 'plot'}
	<figure class="wide"><PlotFigure spec={output} /></figure>
{:else if output.type === 'grid'}
	<figure class="wide grid">
		{#each output.figures as figure, i (i)}
			<PlotFigure spec={figure} />
		{/each}
	</figure>
{/if}

<style>
	figure {
		margin: 0.5rem 0 2rem;
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
