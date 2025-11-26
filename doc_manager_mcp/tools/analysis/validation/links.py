"""Link validation for documentation."""

import re
import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    find_markdown_files,
    get_doc_relative_path,
    safe_resolve,
)
from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.link_index import build_link_index
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser


def extract_links(
    content: str,
    file_path: Path,
    markdown_cache: MarkdownCache | None = None
) -> list[dict[str, Any]]:
    """Extract all links from markdown content."""
    links = []

    # Extract markdown links using cache or parser
    if markdown_cache:
        parsed = markdown_cache.parse(file_path, content)
        md_links = parsed.links
    else:
        parser = MarkdownParser()
        md_links = parser.extract_links(content)

    for link in md_links:
        links.append({
            "text": link["text"],
            "url": link["url"],
            "line": link["line"],
            "file": str(file_path)
        })

    # HTML links: <a href="url"> (fallback for raw HTML)
    html_link_pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\']'
    for match in re.finditer(html_link_pattern, content):
        link_url = match.group(1)
        line_num = content[:match.start()].count('\n') + 1
        links.append({
            "text": "HTML link",
            "url": link_url,
            "line": line_num,
            "file": str(file_path)
        })

    return links


def check_internal_link(
    link_url: str,
    file_path: Path,
    docs_root: Path,
    link_index=None
) -> str | None:
    """Check if internal link is valid using link index for O(1) lookup.

    Args:
        link_url: URL to check
        file_path: Source file containing the link
        docs_root: Documentation root directory
        link_index: Optional LinkIndex for fast lookups (falls back to file system if None)

    Returns:
        Error message if link is broken, None if valid
    """
    # Skip external links and anchors
    if link_url.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
        return None

    # Skip Hugo shortcodes - these are processed at build time
    # Common patterns: {{< relref "..." >}}, {{< ref "..." >}}, {{< ... >}}
    if link_url.startswith(('{{<', '{{%')):
        return None

    # Handle anchor-only links (valid if they reference content in same file)
    if link_url.startswith('#'):
        return None

    # Remove anchor from URL
    url_without_anchor = link_url.split('#')[0]
    if not url_without_anchor:
        return None

    # Use link index if available (performance optimization)
    if link_index is not None:
        # Determine source context for relative links
        if url_without_anchor.startswith('/'):
            # Absolute path from docs root
            source_context = docs_root
        else:
            # Relative to current file's directory
            source_context = file_path.parent

        # O(1) index lookup instead of O(M) iteration or file system check
        target = link_index.resolve(url_without_anchor, source_context, docs_root)

        if target is None:
            return f"Broken link: {link_url} (target not found)"

        return None

    # Fallback to file system checks (backward compatibility)
    # Resolve relative path
    if url_without_anchor.startswith('/'):
        # Absolute path from docs root
        target = docs_root / url_without_anchor.lstrip('/')
    else:
        # Relative to current file
        target = file_path.parent / url_without_anchor

    # Normalize path with recursion depth limit (FR-020)
    try:
        target = safe_resolve(target)
    except RecursionError as e:
        print(f"Warning: {e}", file=sys.stderr)
        return f"Symlink recursion limit exceeded: {link_url}"
    except Exception as e:
        print(f"Warning: Failed to resolve link path {link_url}: {e}", file=sys.stderr)
        return f"Invalid path format: {link_url}"

    # Check if target exists
    if not target.exists():
        # Try with .md extension (Hugo/static site generators often use extensionless links)
        if not target.suffix:
            target_with_md = target.with_suffix('.md')
            if target_with_md.exists():
                return None  # Valid Hugo-style extensionless link

        return f"Broken link: {link_url} (target not found)"

    return None


def check_broken_links(
    docs_path: Path,
    project_path: Path,
    include_root_readme: bool = False,
    markdown_cache: MarkdownCache | None = None,
    markdown_files: list[Path] | None = None
) -> list[dict[str, Any]]:
    """Check for broken internal and external links using link index for performance.

    Args:
        docs_path: Path to documentation directory
        project_path: Project root path
        include_root_readme: Include root README.md
        markdown_cache: Optional markdown cache for performance
        markdown_files: Optional pre-filtered list of files to validate (for incremental mode)

    Returns:
        List of link validation issues
    """
    issues = []
    if markdown_files is None:
        markdown_files = find_markdown_files(
            docs_path,
            project_path=project_path,
            validate_boundaries=False,
            include_root_readme=include_root_readme
        )

    # Build link index once for O(1) lookups instead of O(M) file system checks
    link_index = build_link_index(docs_path)

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            links = extract_links(content, md_file, markdown_cache)

            for link in links:
                # Check internal links only using link index
                error = check_internal_link(link['url'], md_file, docs_path, link_index)
                if error:
                    issues.append({
                        "type": "broken_link",
                        "severity": "error",
                        "file": get_doc_relative_path(md_file, docs_path, project_path),
                        "line": link['line'],
                        "message": error,
                        "link_text": link['text'],
                        "link_url": link['url']
                    })

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": get_doc_relative_path(md_file, docs_path, project_path),
                "line": 1,
                "message": f"Failed to read file: {e!s}"
            })

    return issues
