"""Link rewriter utilities for markdown content.

Handles frontmatter extraction/preservation and link rewriting for documentation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import frontmatter

from ..parsers.markdown import MarkdownParser


def extract_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Extract YAML/TOML/JSON frontmatter from markdown content.

    Uses python-frontmatter library for robust parsing.
    Supports YAML (---), TOML (+++), and JSON frontmatter.

    Args:
        content: Raw markdown content

    Returns:
        Tuple of (frontmatter dict or None, content without frontmatter)

    Examples:
        >>> content = '''---
        ... title: Example
        ... ---
        ... # Content'''
        >>> fm, body = extract_frontmatter(content)
        >>> fm['title']
        'Example'
        >>> body
        '# Content'

        >>> content = '# No frontmatter'
        >>> fm, body = extract_frontmatter(content)
        >>> fm is None
        True
        >>> body
        '# No frontmatter'
    """
    if not content or not isinstance(content, str):
        return None, content or ""

    try:
        post = frontmatter.loads(content)

        # If no frontmatter was found, return None and original content
        if not post.metadata:
            return None, content

        # Return frontmatter dict and content without frontmatter
        return dict(post.metadata), post.content

    except Exception:
        # If parsing fails (malformed frontmatter, etc.), return original content
        # Don't raise - gracefully handle edge cases
        return None, content


def preserve_frontmatter(
    frontmatter_dict: dict[str, Any] | None,
    content: str,
    format: str = "yaml"
) -> str:
    """Reconstruct markdown with frontmatter.

    Args:
        frontmatter_dict: Frontmatter metadata or None
        content: Markdown content without frontmatter
        format: "yaml", "toml", or "json" (default: yaml)

    Returns:
        Complete markdown with frontmatter prepended

    Examples:
        >>> fm = {'title': 'Example', 'date': '2025-01-01'}
        >>> content = '# Content'
        >>> result = preserve_frontmatter(fm, content)
        >>> '---' in result and 'title: Example' in result
        True

        >>> result = preserve_frontmatter(None, '# Content')
        >>> result
        '# Content'
    """
    # If no frontmatter, return content as-is
    if frontmatter_dict is None or not frontmatter_dict:
        return content

    # Validate format
    valid_formats = {"yaml", "toml", "json"}
    if format not in valid_formats:
        format = "yaml"

    # Create a frontmatter Post object
    post = frontmatter.Post(content, **frontmatter_dict)

    # Determine the handler based on format
    if format == "yaml":
        handler = frontmatter.YAMLHandler()
    elif format == "toml":
        # TOMLHandler requires toml package (required dependency)
        toml_handler = getattr(frontmatter, 'TOMLHandler', None)
        if toml_handler is None:
            raise ImportError("TOML support requires 'toml' package. Run: uv add toml")
        handler = toml_handler()
    elif format == "json":
        handler = frontmatter.JSONHandler()
    else:
        handler = frontmatter.YAMLHandler()

    # Export with the specified format
    return frontmatter.dumps(post, handler=handler)


def slugify(text: str) -> str:
    """Convert header text to GitHub-compatible anchor slug.

    Args:
        text: Header text to convert

    Returns:
        Lowercase, hyphenated slug suitable for anchor links

    Example:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("API Reference (v2.0)")
        'api-reference-v20'
    """
    # Convert to lowercase
    slug = text.lower()

    # Remove special characters except spaces and hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)

    # Replace whitespace with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    return slug


def generate_toc(content: str, max_depth: int = 3) -> str:
    """Generate table of contents from markdown headers.

    Args:
        content: Markdown content
        max_depth: Maximum heading level to include (1-6)

    Returns:
        Markdown TOC as unordered list with anchor links

    Example:
        >>> content = "# Title\\n## Section 1\\n### Subsection\\n## Section 2"
        >>> toc = generate_toc(content, max_depth=2)
        >>> print(toc)
        - [Title](#title)
          - [Section 1](#section-1)
          - [Section 2](#section-2)
    """
    parser = MarkdownParser()
    headers = parser.extract_headers(content)

    # Filter by max_depth
    headers = [h for h in headers if h['level'] <= max_depth]

    if not headers:
        return ""

    # Track slugs to handle duplicates
    slug_counts: dict[str, int] = {}
    toc_lines: list[str] = []

    for header in headers:
        level = header['level']
        text = header['text']

        # Generate slug
        slug = slugify(text)

        # Handle duplicate slugs by appending -1, -2, etc.
        if slug in slug_counts:
            slug_counts[slug] += 1
            slug = f"{slug}-{slug_counts[slug]}"
        else:
            slug_counts[slug] = 0

        # Create indented list item
        # Level 1 = no indent, level 2 = 2 spaces, level 3 = 4 spaces, etc.
        indent = '  ' * (level - 1)
        link = f"{indent}- [{text}](#{slug})"
        toc_lines.append(link)

    return '\n'.join(toc_lines)


def update_or_insert_toc(content: str, toc: str, marker: str = "<!-- TOC -->") -> str:
    """Update existing TOC or insert new one.

    Args:
        content: Markdown content
        toc: Generated table of contents
        marker: Comment marker indicating TOC location

    Returns:
        Content with TOC inserted/updated

    Example:
        >>> content = "# Title\\n\\nContent here"
        >>> toc = "- [Title](#title)"
        >>> result = update_or_insert_toc(content, toc)
        >>> "<!-- TOC -->" in result
        True
    """
    end_marker = marker.replace("<!--", "<!--/").replace("<!-- ", "<!-- /")

    # Pattern to match existing TOC section
    toc_pattern = re.compile(
        rf'{re.escape(marker)}.*?{re.escape(end_marker)}',
        re.DOTALL
    )

    # Build new TOC section
    new_toc_section = f"{marker}\n{toc}\n{end_marker}"

    # Check if TOC markers already exist
    if marker in content:
        # Replace existing TOC
        updated_content = toc_pattern.sub(new_toc_section, content)
        return updated_content

    # No existing TOC - insert new one
    # Check for frontmatter (YAML between --- delimiters)
    frontmatter_pattern = re.compile(r'^---\s*\n.*?\n---\s*\n', re.DOTALL | re.MULTILINE)
    frontmatter_match = frontmatter_pattern.match(content)

    if frontmatter_match:
        # Insert after frontmatter
        frontmatter_end = frontmatter_match.end()
        before = content[:frontmatter_end]
        after = content[frontmatter_end:]
        return f"{before}\n{new_toc_section}\n{after}"
    else:
        # Insert at start
        return f"{new_toc_section}\n\n{content}"


def compute_link_mappings(
    content: str,
    file_path: Path,
    old_root: Path,
    new_root: Path,
    project_path: Path
) -> dict[str, str]:
    """Compute link URL transformations when file moves from old_root to new_root.

    Scans markdown content for links and computes how they should be rewritten
    when the file is moved between documentation roots.

    Args:
        content: Markdown content to scan for links
        file_path: Path to file in NEW location
        old_root: Original documentation root
        new_root: New documentation root
        project_path: Project root (for resolving absolute paths)

    Returns:
        Dict mapping old URLs to new URLs

    Example:
        >>> content = "[Guide](../guide.md)"
        >>> old_root = Path("/project/docs")
        >>> new_root = Path("/project/documentation")
        >>> file_path = Path("/project/documentation/api/reference.md")
        >>> mappings = compute_link_mappings(
        ...     content, file_path, old_root, new_root, Path("/project")
        ... )
        >>> # Returns: {"../guide.md": "../guide.md"} (depth unchanged)
    """
    from ..parsers.markdown import MarkdownParser

    mappings = {}

    # Extract all links from content
    parser = MarkdownParser()
    links = parser.extract_links(content)

    # Calculate file's position in old vs new structure
    try:
        # Get file's relative path within new root
        rel_path_in_new = file_path.relative_to(new_root)
        # Construct where file was in old structure (same relative path)
        old_file_path = old_root / rel_path_in_new
        old_file_dir = old_file_path.parent
        new_file_dir = file_path.parent
    except ValueError:
        # File not under new_root, can't compute mappings
        return mappings

    for link in links:
        url = link.get("url", "")

        # Skip external links
        if url.startswith(("http://", "https://", "ftp://", "mailto:", "#")):
            continue

        # Skip empty or anchor-only links
        if not url or url.startswith("#"):
            continue

        try:
            # Resolve the link target from old location
            if url.startswith("/"):
                # Absolute path from project root
                old_target = project_path / url.lstrip("/")
            else:
                # Relative path from old file location
                old_target = (old_file_dir / url).resolve()

            # Check if target exists or will exist in new structure
            # Try to find it relative to new root
            try:
                target_rel_to_old_root = old_target.relative_to(old_root)
                new_target = new_root / target_rel_to_old_root
            except ValueError:
                # Target is outside old_root, try relative to project
                try:
                    target_rel_to_project = old_target.relative_to(project_path)
                    new_target = project_path / target_rel_to_project
                except ValueError:
                    # Can't resolve, skip this link
                    continue

            # Compute new relative path from new file location to new target
            new_url = compute_relative_link(new_file_dir, new_target, new_root)

            # Only add mapping if URL changed
            if new_url != url:
                mappings[url] = new_url

        except (ValueError, OSError):
            # Link resolution failed, skip
            continue

    return mappings


def rewrite_links_in_content(content: str, mappings: dict[str, str]) -> str:
    """Apply link mappings to markdown content.

    Handles:
    - Inline links: [text](url)
    - Reference links: [text][ref] and [ref]: url definitions
    - Preserves external links (http://, https://)
    - Skips links in code blocks (fenced code blocks preserved)
    - Handles escaped links (\\[text](url) not modified)
    - Gracefully handles Hugo shortcodes (preserved as-is)

    Args:
        content: Markdown content
        mappings: URL transformations (old -> new)

    Returns:
        Content with rewritten links

    Example:
        >>> content = "[Guide](../old/guide.md)"
        >>> mappings = {"../old/guide.md": "../new/guide.md"}
        >>> rewrite_links_in_content(content, mappings)
        '[Guide](../new/guide.md)'
    """
    if not mappings:
        return content

    # Extract code blocks to preserve them
    parser = MarkdownParser()
    code_blocks = parser.extract_code_blocks(content)

    # Create placeholder map for code blocks
    code_placeholders = {}
    modified_content = content

    # Replace code blocks with placeholders to protect them
    for i, block in enumerate(code_blocks):
        placeholder = f"___CODE_BLOCK_{i}___"
        # Reconstruct the fenced code block
        lang = block.get('language', '')
        code = block.get('code', '')
        fence = f"```{lang}\n{code}```"

        # Find and replace this code block (only first occurrence)
        modified_content = modified_content.replace(fence, placeholder, 1)
        code_placeholders[placeholder] = fence

    # Pattern for inline links: [text](url)
    # Negative lookbehind to avoid escaped links \[text](url)
    inline_link_pattern = re.compile(
        r'(?<!\\)\[([^\]]+)\]\(([^)]+)\)'
    )

    def replace_inline_link(match: re.Match[str]) -> str:
        """Replace a single inline link if it's in mappings."""
        text = match.group(1)
        url = match.group(2)

        # Don't modify external links
        if _is_external_link(url):
            return match.group(0)

        # Apply mapping if URL is in mappings
        new_url = mappings.get(url, url)

        return f"[{text}]({new_url})"

    # Apply inline link replacements
    modified_content = inline_link_pattern.sub(replace_inline_link, modified_content)

    # Pattern for reference-style link definitions: [ref]: url "optional title"
    # Must be at start of line (after optional whitespace)
    ref_def_pattern = re.compile(
        r'(?m)^\s*\[([^\]]+)\]:\s*([^\s]+)(?:\s+"([^"]*)")?'
    )

    def replace_ref_definition(match: re.Match[str]) -> str:
        """Replace reference definition URL if in mappings."""
        indent = match.group(0)[:match.start(1) - match.start(0) - 1]  # Preserve indentation
        ref_id = match.group(1)
        url = match.group(2)
        title = match.group(3)

        # Don't modify external links
        if _is_external_link(url):
            return match.group(0)

        # Apply mapping
        new_url = mappings.get(url, url)

        # Reconstruct the reference definition with original indentation
        if title:
            return f'{indent}[{ref_id}]: {new_url} "{title}"'
        else:
            return f'{indent}[{ref_id}]: {new_url}'

    # Apply reference definition replacements
    modified_content = ref_def_pattern.sub(replace_ref_definition, modified_content)

    # Restore code blocks from placeholders
    for placeholder, original_code in code_placeholders.items():
        modified_content = modified_content.replace(placeholder, original_code)

    return modified_content


def _is_external_link(url: str) -> bool:
    """Check if a URL is external (http/https/ftp).

    Args:
        url: URL to check

    Returns:
        True if URL is external, False otherwise

    Example:
        >>> _is_external_link("https://example.com")
        True
        >>> _is_external_link("../guide.md")
        False
    """
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https', 'ftp', 'ftps')


def compute_relative_link(
    from_file: Path,
    to_file: Path,
    from_root: Path
) -> str:
    """Compute relative link from one file to another.

    Args:
        from_file: Source file path
        to_file: Target file path
        from_root: Documentation root path

    Returns:
        Relative URL from source to target

    Example:
        >>> from_file = Path("/docs/guide/setup.md")
        >>> to_file = Path("/docs/api/reference.md")
        >>> root = Path("/docs")
        >>> compute_relative_link(from_file, to_file, root)
        '../api/reference.md'
    """
    try:
        # Make both paths relative to root
        from_rel = from_file.relative_to(from_root)
        to_rel = to_file.relative_to(from_root)

        # Compute relative path from source directory to target
        from_dir = from_rel.parent

        # Calculate how many levels up we need to go
        up_levels = len(from_dir.parts)

        # Build the relative path
        if up_levels == 0:
            # Same directory
            relative = to_rel
        else:
            # Go up and then down to target
            relative = Path("../" * up_levels) / to_rel

        # Convert to forward slashes for URLs
        return str(relative).replace("\\", "/")

    except ValueError:
        # Files not under same root, return absolute path
        return str(to_file)


def extract_hugo_shortcodes(content: str) -> list[dict[str, Any]]:
    """Extract Hugo shortcodes from content.

    Hugo shortcodes have format: {{< shortcode params >}} or {{% shortcode %}}

    Args:
        content: Markdown content

    Returns:
        List of dicts with keys: type, content, line

    Example:
        >>> content = '{{< ref "guide.md" >}}'
        >>> extract_hugo_shortcodes(content)
        [{'type': 'ref', 'content': '"guide.md"', 'line': 1}]
    """
    shortcodes = []

    # Pattern for {{< shortcode >}} style (no HTML escaping)
    angle_pattern = re.compile(
        r'\{\{<\s*(\w+)\s+([^>]+)>\}\}'
    )

    # Pattern for {{% shortcode %}} style (with HTML escaping)
    percent_pattern = re.compile(
        r'\{\{%\s*(\w+)\s+([^%]+)%\}\}'
    )

    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Find angle bracket shortcodes
        for match in angle_pattern.finditer(line):
            shortcodes.append({
                'type': match.group(1),
                'content': match.group(2).strip(),
                'line': line_num
            })

        # Find percent shortcodes
        for match in percent_pattern.finditer(line):
            shortcodes.append({
                'type': match.group(1),
                'content': match.group(2).strip(),
                'line': line_num
            })

    return shortcodes
