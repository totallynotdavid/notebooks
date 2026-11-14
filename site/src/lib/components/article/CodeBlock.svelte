<script lang="ts">
	/** Longer fences start folded so the prose stays readable. */
	const FOLD_LINES = 14;

	let { html }: { html: string } = $props();

	const lines = $derived((html.match(/class="line"/g) ?? []).length);
</script>

{#if lines > FOLD_LINES}
	<details class="code">
		<summary lang="en">Show code ({lines} lines)</summary>
		<!-- Highlighted at build time by Shiki. -->
		{@html html}
	</details>
{:else}
	<div class="code">{@html html}</div>
{/if}

<style>
	.code {
		margin: 0 0 1.5rem;
	}
	summary {
		width: fit-content;
		padding: 0.3rem 0;
		font-family: var(--font-mono);
		font-size: var(--text-label);
		color: var(--accent);
		cursor: pointer;
	}
	.code :global(pre) {
		overflow-x: auto;
		margin: 0;
		padding: 0.9rem 1rem;
		background: var(--code-bg) !important;
		border-radius: var(--radius);
		font: 0.85rem / 1.55 var(--font-mono);
	}
	details[open] summary {
		margin-bottom: 0.5rem;
	}
	.code :global(.shiki span) {
		color: var(--shiki-light);
	}
	@media (prefers-color-scheme: dark) {
		.code :global(.shiki span) {
			color: var(--shiki-dark);
		}
	}
</style>
