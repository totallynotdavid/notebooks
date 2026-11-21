<script lang="ts">
	import type { Site, Topic } from '#lib/catalog.generated.js';

	let { site, topics }: { site: Site; topics: Topic[] } = $props();
</script>

<footer class="footer">
	<div class="footer__inner">
		<nav class="footer__column" aria-label="Temas">
			<h2 class="footer__heading">Temas</h2>
			<ul>
				{#each topics as topic (topic.id)}
					<li><a href="?topic={topic.id}">{topic.title}</a></li>
				{/each}
			</ul>
		</nav>

		<nav class="footer__column" aria-label="Proyecto">
			<h2 class="footer__heading">Proyecto</h2>
			<ul>
				<li><a href={site.repository} rel="external noopener">Código en GitHub ↗</a></li>
				<li><a href="{site.repository}/issues" rel="external noopener">Reportar un problema ↗</a></li>
				<li><a href="{site.repository}/blob/HEAD/LICENSE" rel="external noopener">Licencia MIT ↗</a></li>
			</ul>
		</nav>
	</div>
</footer>

<style>
	.footer {
		padding: 3.5rem 0 calc(3rem + env(safe-area-inset-bottom));
		background: var(--deemphasized);
		color: var(--content-secondary);
		font: var(--text-label) / 1.6 var(--font-base);
	}
	.footer__inner {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 2.5rem 3rem;
		max-width: var(--layout-width);
		margin: 0 auto;
		padding: 0 var(--gutter);
	}
	.footer__heading {
		margin: 0 0 1rem;
		color: var(--content-secondary);
		font: 500 0.75rem var(--font-mono);
		letter-spacing: 0.06em;
		text-transform: uppercase;
	}
	.footer__column ul {
		display: grid;
		gap: 0.6rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.footer__column a {
		color: var(--content);
		transition: color 150ms ease-out;
	}
	.footer__column a:hover {
		color: var(--accent);
	}

	@media (min-width: 768px) {
		.footer__inner {
			grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		}
	}
</style>
