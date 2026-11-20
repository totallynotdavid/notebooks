"""Markdown articles with Python fences, rendered by the notebooks site."""

from quire import plot
from quire.cache import cache
from quire.execute import article_namespace
from quire.outputs import md, table
from quire.parameter import parameter

__all__ = ["article_namespace", "cache", "md", "parameter", "plot", "table"]
