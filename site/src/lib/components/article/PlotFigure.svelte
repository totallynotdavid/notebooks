<script lang="ts">
	import { readPalette, renderPlot } from '#lib/article/plot.js';
	import type { PlotSpec } from '#lib/article/types.js';

	let { spec }: { spec: PlotSpec } = $props();

	let width = $state(0);
	let frame = $state(0);
	let playing = $state(false);
	let canvas: HTMLDivElement | undefined = $state();

	const frames = $derived(spec.frames);
	// A figure's own width is a maximum; it still shrinks with the column.
	const plotWidth = $derived(
		typeof spec.options.width === 'number' ? Math.min(width, spec.options.width) : width
	);
	const last = $derived((frames?.labels.length ?? 1) - 1);
	// Room for the plot before it draws on the client, so the page does not shift.
	const reserved = $derived(
		typeof spec.options.height === 'number' ? spec.options.height : spec.options.aspectRatio ? 0 : 400
	);

	$effect(() => {
		if (!canvas || width === 0) return;
		canvas.replaceChildren(renderPlot(spec, frame, plotWidth, readPalette(canvas)));
	});

	$effect(() => {
		if (!playing || !frames) return;
		const step = 1000 / frames.fps;
		let previous = performance.now();
		let request = requestAnimationFrame(function tick(now) {
			if (now - previous >= step) {
				previous = now;
				if (frame >= last) {
					playing = false;
					return;
				}
				frame += 1;
			}
			request = requestAnimationFrame(tick);
		});
		return () => cancelAnimationFrame(request);
	});

	function toggle() {
		if (!playing && frame >= last) frame = 0;
		playing = !playing;
	}
</script>

<div class="plot" bind:clientWidth={width}>
	<div class="plot__canvas" bind:this={canvas} style:min-height="{reserved}px"></div>
	{#if frames}
		<div class="plot__player" style:max-width="{plotWidth}px">
			<button type="button" class="plot__toggle" onclick={toggle} aria-label={playing ? 'Pause' : 'Play'}>
				{#if playing}
					<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z" /></svg>
				{:else}
					<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" /></svg>
				{/if}
			</button>
			<input
				class="plot__scrubber"
				type="range"
				min="0"
				max={last}
				bind:value={frame}
				oninput={() => (playing = false)}
				aria-label="Frame"
			/>
			<output class="plot__label">{frames.labels[frame]}</output>
		</div>
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
	.plot__player {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin: 0.5rem auto 0;
		font-family: var(--font-mono);
		font-size: var(--text-label);
	}
	.plot__toggle {
		display: grid;
		place-items: center;
		flex-shrink: 0;
		width: 2.25rem;
		height: 2.25rem;
		padding: 0;
		background: transparent;
		border: 1px solid var(--content);
		border-radius: var(--radius);
		color: var(--content);
		cursor: pointer;
		transition: background 150ms ease-out, color 150ms ease-out;
	}
	.plot__toggle:hover {
		background: var(--content);
		color: var(--page);
	}
	.plot__toggle:active {
		transform: scale(0.96);
	}
	.plot__toggle:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.plot__toggle svg {
		width: 1rem;
		height: 1rem;
		fill: currentColor;
	}
	.plot__scrubber {
		flex: 1;
		min-width: 0;
		accent-color: var(--accent);
	}
	.plot__label {
		min-width: 9ch;
		color: var(--content-secondary);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
</style>
