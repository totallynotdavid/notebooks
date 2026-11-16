<script lang="ts">
	import type { FigureSpec, LazyFigure } from '#lib/article/types.js';

	import Output from './Output.svelte';

	let { lazy, src }: { lazy: LazyFigure; src: string } = $props();

	let root: HTMLDivElement | undefined = $state();
	let spec: FigureSpec | undefined = $state();
	let failed = $state(false);

	// Fetch a screen ahead of the reader, so the figure is usually drawn by the
	// time it scrolls into view.
	$effect(() => {
		if (!root) return;
		const observer = new IntersectionObserver(
			([entry]) => {
				if (!entry.isIntersecting) return;
				observer.disconnect();
				fetch(src)
					.then((response) => {
						if (!response.ok) throw new Error(`${src}: ${response.status}`);
						return response.json() as Promise<FigureSpec>;
					})
					.then((figure) => (spec = figure))
					.catch(() => (failed = true));
			},
			{ rootMargin: '100% 0px' }
		);
		observer.observe(root);
		return () => observer.disconnect();
	});
</script>

{#if spec}
	<Output output={spec} />
{:else}
	<div class="wide placeholder" bind:this={root} style:height="{lazy.height}px">
		{#if failed}
			<p>No se pudo cargar la figura. Recarga la página para intentarlo de nuevo.</p>
		{/if}
	</div>
{/if}

<style>
	.placeholder {
		display: grid;
		place-items: center;
		margin: var(--figure-margin);
		border-radius: var(--radius);
		background: var(--code-bg);
		color: var(--content-secondary);
		font-size: var(--text-label);
	}
</style>
