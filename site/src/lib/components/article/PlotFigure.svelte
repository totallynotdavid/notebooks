<script lang="ts">
	import { readPalette, renderPlot } from '#lib/article/plot.js';
	import type { PlotSpec } from '#lib/article/types.js';

	import Player from './Player.svelte';

	// A grid that shares one player passes `frame` in and turns `player` off.
	let {
		spec,
		frame = $bindable(0),
		player = true
	}: { spec: PlotSpec; frame?: number; player?: boolean } = $props();

	let width = $state(0);
	let canvas: HTMLDivElement | undefined = $state();

	// A figure's own width is a maximum; it still shrinks with the column.
	const plotWidth = $derived(
		typeof spec.options.width === 'number' ? Math.min(width, spec.options.width) : width
	);
	// Room for the plot before it draws on the client, so the page does not shift.
	const reserved = $derived(
		typeof spec.options.height === 'number' ? spec.options.height : spec.options.aspectRatio ? 0 : 400
	);

	$effect(() => {
		if (!canvas || width === 0) return;
		canvas.replaceChildren(renderPlot(spec, frame, plotWidth, readPalette(canvas)));
	});
</script>

<div class="plot" bind:clientWidth={width}>
	<div class="plot__canvas" bind:this={canvas} style:min-height="{reserved}px"></div>
	{#if spec.frames && player}
		<Player labels={spec.frames.labels} fps={spec.frames.fps} bind:frame maxWidth={plotWidth} />
	{/if}
</div>

<style>
	.plot {
		min-width: 0;
	}
	.plot__canvas :global(figure) {
		width: fit-content;
		max-width: 100%;
		margin: 0 auto;
	}
	.plot__canvas :global(h2) {
		margin: 0 0 0.25rem;
		font-size: var(--text-body);
		line-height: 1.4;
		text-wrap: balance;
	}
	/* Plot's stylesheet sets the tip fill to white on the svg itself. */
	.plot__canvas :global(svg) {
		display: block;
		--plot-background: var(--page);
	}
	/* Plot styles its legend apart from the chart, in a system font. */
	.plot__canvas :global([class*='-swatches']) {
		font-family: var(--font-mono);
		font-size: 12px;
	}
</style>
