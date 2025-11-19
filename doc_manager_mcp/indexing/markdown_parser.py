"""Markdown structure parser using markdown-it-py.

This module provides the MarkdownParser class for extracting structured data
from markdown files, including headers, links, images, and code blocks with
line number information.
"""

from __future__ import annotations

from typing import Any

import markdown_it


class MarkdownParser:
    """Parse markdown document structure using markdown-it-py.

    Extracts from markdown files:
    - Headers (with levels and line numbers)
    - Links (inline, reference, autolinks)
    - Images (with alt text and line numbers)
    - Code blocks (with language tags and line numbers)
    - Inline code spans (with line numbers)

    All extracted elements include line number information via the token.map
    attribute provided by markdown-it-py.
    """

    def __init__(self):
        """Initialize the markdown parser."""
        self.md_parser = markdown_it.MarkdownIt()

    def extract_headers(self, content: str) -> list[dict[str, Any]]:
        """Extract markdown headers with level, text, and line number.

        Args:
            content: Markdown content as string

        Returns:
            List of dicts with keys: level, text, line

        Example:
            >>> parser = MarkdownParser()
            >>> headers = parser.extract_headers("# Title\\n## Subtitle")
            >>> headers
            [{'level': 1, 'text': 'Title', 'line': 1},
             {'level': 2, 'text': 'Subtitle', 'line': 2}]
        """
        tokens = self.md_parser.parse(content)
        headers = []

        for i, token in enumerate(tokens):
            if token.type == 'heading_open':
                # Extract level from tag (h1 -> 1, h2 -> 2, etc.)
                level = int(token.tag[1])

                # Next token contains the heading text
                text = ""
                if i + 1 < len(tokens):
                    text_token = tokens[i + 1]
                    if text_token.type == 'inline':
                        text = text_token.content

                # Get line number from map attribute
                line = token.map[0] + 1 if token.map else None

                headers.append({
                    "level": level,
                    "text": text,
                    "line": line
                })

        return headers

    def extract_links(self, content: str) -> list[dict[str, Any]]:
        """Extract all markdown links with text, URL, and line number.

        Extracts:
        - Inline links: [text](url)
        - Reference links: [text][ref] (includes the link itself, not definition)
        - Autolinks: <http://example.com>

        Args:
            content: Markdown content as string

        Returns:
            List of dicts with keys: type, text, url, line

        Example:
            >>> parser = MarkdownParser()
            >>> links = parser.extract_links("[Example](http://example.com)")
            >>> links
            [{'type': 'inline', 'text': 'Example', 'url': 'http://example.com', 'line': 1}]
        """
        tokens = self.md_parser.parse(content)
        links = []

        # Links are children of inline tokens, not top-level
        for token in tokens:
            if token.type == 'inline' and hasattr(token, 'children') and token.children:
                # Get line number from parent inline token
                line = token.map[0] + 1 if token.map else None

                # Search for link_open in children
                i = 0
                while i < len(token.children):
                    child = token.children[i]

                    if child.type == 'link_open':
                        # Extract URL from href attribute
                        href = ""
                        if child.attrs:
                            attrs_dict = dict(child.attrs)
                            href = attrs_dict.get('href', '')

                        # Next child should be text with link text
                        text = ""
                        if i + 1 < len(token.children):
                            text_child = token.children[i + 1]
                            if text_child.type == 'text':
                                text = text_child.content

                        links.append({
                            "type": "inline",
                            "text": text,
                            "url": href,
                            "line": line
                        })

                    i += 1

        return links

    def extract_code_blocks(self, content: str) -> list[dict[str, Any]]:
        """Extract fenced code blocks with language, content, and line number.

        Args:
            content: Markdown content as string

        Returns:
            List of dicts with keys: language, code, line

        Example:
            >>> parser = MarkdownParser()
            >>> blocks = parser.extract_code_blocks("```python\\nprint('hello')\\n```")
            >>> blocks
            [{'language': 'python', 'code': "print('hello')\\n", 'line': 1}]
        """
        tokens = self.md_parser.parse(content)
        code_blocks = []

        for token in tokens:
            if token.type == 'fence':
                language = token.info.strip() if token.info else None
                code = token.content
                line = token.map[0] + 1 if token.map else None

                code_blocks.append({
                    "language": language,
                    "code": code,
                    "line": line
                })

        return code_blocks

    def extract_images(self, content: str) -> list[dict[str, Any]]:
        """Extract markdown images with alt text, src, and line number.

        Args:
            content: Markdown content as string

        Returns:
            List of dicts with keys: alt, src, line

        Example:
            >>> parser = MarkdownParser()
            >>> images = parser.extract_images("![Alt text](image.png)")
            >>> images
            [{'alt': 'Alt text', 'src': 'image.png', 'line': 1}]
        """
        tokens = self.md_parser.parse(content)
        images = []

        # Images are children of inline tokens, like links
        for token in tokens:
            if token.type == 'inline' and hasattr(token, 'children') and token.children:
                # Get line number from parent inline token
                line = token.map[0] + 1 if token.map else None

                # Search for image in children
                for child in token.children:
                    if child.type == 'image':
                        # Extract src from src attribute
                        src = ""
                        if child.attrs:
                            attrs_dict = dict(child.attrs)
                            src = attrs_dict.get('src', '')

                        # Alt text is in content
                        alt = child.content if child.content else ""

                        images.append({
                            "alt": alt,
                            "src": src,
                            "line": line
                        })

        return images

    def extract_inline_code(self, content: str) -> list[dict[str, Any]]:
        """Extract inline code spans with content and line number.

        Args:
            content: Markdown content as string

        Returns:
            List of dicts with keys: text, line

        Example:
            >>> parser = MarkdownParser()
            >>> code = parser.extract_inline_code("Use `functionName()` here")
            >>> code
            [{'text': 'functionName()', 'line': 1}]
        """
        tokens = self.md_parser.parse(content)
        inline_codes = []

        # Need to traverse inline tokens within other tokens
        def _extract_from_inline(token: Any, base_line: int | None) -> None:
            """Recursively extract inline code from token children."""
            if token.type == 'code_inline':
                inline_codes.append({
                    "text": token.content,
                    "line": base_line
                })

            # Check children if present
            if hasattr(token, 'children') and token.children:
                for child in token.children:
                    _extract_from_inline(child, base_line)

        # Process all tokens
        for token in tokens:
            line = token.map[0] + 1 if token.map else None

            if token.type == 'inline':
                # Inline tokens contain children that might be code_inline
                if hasattr(token, 'children') and token.children:
                    for child in token.children:
                        _extract_from_inline(child, line)

        return inline_codes
