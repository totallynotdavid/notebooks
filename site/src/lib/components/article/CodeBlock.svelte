<script lang="ts">
	let { html }: { html: string } = $props();
</script>

<!-- Highlighted at build time by Shiki. -->
<div class="code">{@html html}</div>

<style>
	.code {
		margin: 0 0 1.5rem;
	}
	/* Code shows only when the reader turns it on; see lib/article/code.ts. */
	:global(html:not([data-code])) .code {
		display: none;
	}
	.code :global(pre) {
		overflow-x: auto;
		margin: 0;
		padding: 0.9rem 1rem;
		background: var(--code-bg) !important;
		border-radius: var(--radius);
		font: 0.85rem / 1.55 var(--font-mono);
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
