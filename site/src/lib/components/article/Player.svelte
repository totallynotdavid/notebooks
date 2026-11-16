<script lang="ts">
	let {
		labels,
		fps,
		frame = $bindable(0),
		maxWidth
	}: { labels: string[]; fps: number; frame?: number; maxWidth?: number } = $props();

	let playing = $state(false);
	const last = $derived(labels.length - 1);

	$effect(() => {
		if (!playing) return;
		const step = 1000 / fps;
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

<div class="player" style:max-width={maxWidth ? `${maxWidth}px` : null}>
	<button type="button" class="player__toggle" onclick={toggle} aria-label={playing ? 'Pause' : 'Play'}>
		{#if playing}
			<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zM9 3h3v10H9z" /></svg>
		{:else}
			<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" /></svg>
		{/if}
	</button>
	<input
		class="player__scrubber"
		type="range"
		min="0"
		max={last}
		bind:value={frame}
		oninput={() => (playing = false)}
		aria-label="Frame"
	/>
	<output class="player__label">{labels[frame]}</output>
</div>

<style>
	.player {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin: 0.5rem auto 0;
		font-family: var(--font-mono);
		font-size: var(--text-label);
	}
	.player__toggle {
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
	.player__toggle:hover {
		background: var(--content);
		color: var(--page);
	}
	.player__toggle:active {
		transform: scale(0.96);
	}
	.player__toggle:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.player__toggle svg {
		width: 1rem;
		height: 1rem;
		fill: currentColor;
	}
	.player__scrubber {
		flex: 1;
		min-width: 0;
		accent-color: var(--accent);
	}
	.player__label {
		min-width: 9ch;
		color: var(--content-secondary);
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
</style>
