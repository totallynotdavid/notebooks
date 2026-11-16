<script lang="ts">
	import type { Site, Topic } from '#lib/catalog.generated.js';

	let { site, topics }: { site: Site; topics: Topic[] } = $props();
</script>

<footer class="footer">
	<div class="footer__inner">
		<div class="footer__about">
			<p class="footer__lead">
				Computational physics notebooks in Spanish, each published as a page of its results.
			</p>
			<p>
				Your browser runs no Python. To rerun a notebook with other parameters, clone the repository
				and build it with <a href="{site.repository}#readme" rel="external noopener">one command</a>.
			</p>
		</div>

		<nav class="footer__column" aria-label="Topics">
			<h2 class="footer__heading">Topics</h2>
			<ul>
				{#each topics as topic (topic.id)}
					<li><a href="?topic={topic.id}">{topic.title}</a></li>
				{/each}
			</ul>
		</nav>

		<nav class="footer__column" aria-label="Project">
			<h2 class="footer__heading">Project</h2>
			<ul>
				<li><a href={site.repository} rel="external noopener">Source on GitHub ↗</a></li>
				<li><a href="{site.repository}/issues" rel="external noopener">Report a problem ↗</a></li>
				<li><a href="{site.repository}/blob/HEAD/LICENSE" rel="external noopener">MIT license ↗</a></li>
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
	.footer__about {
		max-width: 26rem;
	}
	.footer__about p {
		margin: 0;
		text-wrap: pretty;
	}
	.footer__about p + p {
		margin-top: 0.75rem;
	}
	.footer__lead {
		color: var(--content);
		font-size: var(--text-body);
	}
	.footer__about a {
		color: var(--content);
		text-decoration: underline;
		text-decoration-color: var(--content-secondary);
		text-underline-offset: 0.2em;
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
	.footer__about a:hover,
	.footer__column a:hover {
		color: var(--accent);
	}

	@media (min-width: 768px) {
		.footer__inner {
			grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 0.8fr);
		}
	}
</style>
