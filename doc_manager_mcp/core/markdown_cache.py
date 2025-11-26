"""Markdown parsing cache for performance optimization.

This module provides caching for parsed markdown content to avoid redundant
parsing operations in validate_docs and assess_quality.

Performance improvement: Eliminates 6x parsing in validate_docs and 7x in
assess_quality (13x total when both tools run).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser


@dataclass
class ParsedMarkdown:
    """Cached parsed markdown content.

    Stores all commonly-needed parsed components to avoid re-parsing.
    Components are stored as returned by MarkdownParser (dicts with metadata).
    """

    headings: list[dict[str, Any]]  # Headers with level, text, line
    links: list[dict[str, Any]]  # Links with text, url, line
    images: list[dict[str, Any]]  # Images with alt, src, line
    code_blocks: list[dict[str, Any]]  # Code blocks with language, code, line


class MarkdownCache:
    """Cache for parsed markdown files.

    Caches parsed markdown content keyed by file path. Avoids redundant
    parsing when multiple validators or quality criteria need the same
    parsed data.

    Example:
        cache = MarkdownCache()

        # First parse - parses and caches
        parsed1 = cache.parse(file_path, content)

        # Second parse - returns cached (no parsing)
        parsed2 = cache.parse(file_path, content)
        assert parsed1 is parsed2  # Same object
    """

    def __init__(self):
        """Initialize empty cache."""
        self._cache: dict[Path, ParsedMarkdown] = {}

    def parse(self, file_path: Path, content: str) -> ParsedMarkdown:
        """Parse markdown content, using cache if available.

        Args:
            file_path: Path to markdown file (used as cache key)
            content: Markdown content to parse

        Returns:
            ParsedMarkdown with extracted components
        """
        # Check cache first
        if file_path in self._cache:
            return self._cache[file_path]

        # Parse markdown using existing parser
        parser = MarkdownParser()

        # Extract all components (using correct method names)
        headings = parser.extract_headers(content)
        links = parser.extract_links(content)
        images = parser.extract_images(content)
        code_blocks = parser.extract_code_blocks(content)

        # Cache the parsed result
        parsed = ParsedMarkdown(
            headings=headings,
            links=links,
            images=images,
            code_blocks=code_blocks
        )

        self._cache[file_path] = parsed
        return parsed

    def clear(self):
        """Clear all cached parsed content.

        Use this when:
        - Starting a new validation/quality assessment session
        - File content has changed
        - Running in watch mode with file modifications
        """
        self._cache.clear()

    def __len__(self) -> int:
        """Return number of cached files."""
        return len(self._cache)

    def __contains__(self, file_path: Path) -> bool:
        """Check if file is in cache."""
        return file_path in self._cache
