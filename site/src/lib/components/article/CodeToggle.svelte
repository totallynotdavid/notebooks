<script lang="ts">
	import { onMount } from 'svelte';

	import { codeShown, showCode } from '#lib/article/code.js';

	let shown = $state(false);

	onMount(() => {
		shown = codeShown();
	});

	function toggle() {
		shown = !shown;
		showCode(shown);
	}
</script>

<button type="button" class="toggle" class:toggle--on={shown} onclick={toggle}>
	<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5.5 4 1.5 8l4 4M10.5 4l4 4-4 4" /></svg>
	<span class="toggle__label">{shown ? 'Ocultar código' : 'Mostrar código'}</span>
</button>

<style>
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0.7rem;
		background: transparent;
		border: 1px solid var(--line);
		border-radius: var(--radius);
		color: var(--content);
		font: var(--text-label) var(--font-mono);
		white-space: nowrap;
		cursor: pointer;
		transition: background 150ms ease-out;
	}
	.toggle:hover,
	.toggle--on {
		background: var(--code-bg);
	}
	.toggle:active {
		transform: scale(0.97);
	}
	.toggle:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	/* A phone keeps the header's width for the topic name; the label stays for screen readers. */
	@media (max-width: 640px) {
		.toggle {
			padding: 0.45rem;
		}
		.toggle__label {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip: rect(0, 0, 0, 0);
			white-space: nowrap;
		}
	}
	svg {
		width: 1rem;
		height: 1rem;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.5;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
</style>
