"""Documentation validation tools for doc-manager."""

import asyncio
import re
import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    enforce_response_limit,
    find_docs_directory,
    find_markdown_files,
    get_doc_relative_path,
    handle_error,
    load_config,
    load_conventions,
    safe_resolve,
    validate_against_conventions,
)
from doc_manager_mcp.indexing.analysis.code_validator import CodeValidator
from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.analysis.tree_sitter import SymbolIndexer
from doc_manager_mcp.indexing.link_index import build_link_index
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser
from doc_manager_mcp.models import ValidateDocsInput

from .helpers import validate_code_examples, validate_documented_symbols


def _extract_links(content: str, file_path: Path, markdown_cache: MarkdownCache | None = None) -> list[dict[str, Any]]:
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


def _check_internal_link(link_url: str, file_path: Path, docs_root: Path, link_index=None) -> str | None:
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


def _check_broken_links(docs_path: Path, project_path: Path, include_root_readme: bool = False, markdown_cache: MarkdownCache | None = None) -> list[dict[str, Any]]:
    """Check for broken internal and external links using link index for performance."""
    issues = []
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

            links = _extract_links(content, md_file, markdown_cache)

            for link in links:
                # Check internal links only using link index
                error = _check_internal_link(link['url'], md_file, docs_path, link_index)
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


def _extract_images(content: str, file_path: Path, markdown_cache: MarkdownCache | None = None) -> list[dict[str, Any]]:
    """Extract all images from markdown content."""
    images = []

    # Extract markdown images using cache or parser
    if markdown_cache:
        parsed = markdown_cache.parse(file_path, content)
        md_images = parsed.images
    else:
        parser = MarkdownParser()
        md_images = parser.extract_images(content)

    for img in md_images:
        images.append({
            "alt": img["alt"],
            "src": img["src"],
            "line": img["line"],
            "file": str(file_path)
        })

    # HTML images: <img src="..." alt="..."> (fallback for raw HTML)
    html_image_pattern = r'<img\s+[^>]*src=["\']([^"\']+)["\'](?:[^>]*alt=["\']([^"\']*)["\'])?'
    for match in re.finditer(html_image_pattern, content):
        image_src = match.group(1)
        alt_text = match.group(2) or ""
        line_num = content[:match.start()].count('\n') + 1
        images.append({
            "alt": alt_text,
            "src": image_src,
            "line": line_num,
            "file": str(file_path)
        })

    return images


def _validate_assets(docs_path: Path, project_path: Path, include_root_readme: bool = False, markdown_cache: MarkdownCache | None = None) -> list[dict[str, Any]]:
    """Validate asset links and alt text."""
    issues = []
    markdown_files = find_markdown_files(
        docs_path,
        project_path=project_path,
        validate_boundaries=False,
        include_root_readme=include_root_readme
    )

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            images = _extract_images(content, md_file, markdown_cache)

            for img in images:
                # Check for missing alt text
                if not img['alt'].strip():
                    issues.append({
                        "type": "missing_alt_text",
                        "severity": "warning",
                        "file": get_doc_relative_path(md_file, docs_path, project_path),
                        "line": img['line'],
                        "message": f"Image missing alt text: {img['src']}",
                        "image_src": img['src']
                    })

                # Check if image file exists (for local images only)
                if not img['src'].startswith(('http://', 'https://', 'data:')):
                    # Remove anchor/query params
                    image_url = img['src'].split('#')[0].split('?')[0]

                    if image_url.startswith('/'):
                        image_path = docs_path / image_url.lstrip('/')
                    else:
                        image_path = md_file.parent / image_url

                    try:
                        image_path = safe_resolve(image_path)
                        if not image_path.exists():
                            issues.append({
                                "type": "missing_asset",
                                "severity": "error",
                                "file": get_doc_relative_path(md_file, docs_path, project_path),
                                "line": img['line'],
                                "message": f"Image file not found: {img['src']}",
                                "image_src": img['src']
                            })
                    except Exception as e:
                        print(f"Warning: Failed to resolve image path {img['src']}: {e}", file=sys.stderr)
                        issues.append({
                            "type": "invalid_asset_path",
                            "severity": "error",
                            "file": get_doc_relative_path(md_file, docs_path, project_path),
                            "line": img['line'],
                            "message": f"Invalid image path: {img['src']}",
                            "image_src": img['src']
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


def _extract_code_blocks(content: str, file_path: Path, markdown_cache: MarkdownCache | None = None) -> list[dict[str, Any]]:
    """Extract code blocks from markdown content."""
    code_blocks = []

    # Extract fenced code blocks using cache or parser
    if markdown_cache:
        parsed = markdown_cache.parse(file_path, content)
        blocks = parsed.code_blocks
    else:
        parser = MarkdownParser()
        blocks = parser.extract_code_blocks(content)

    for block in blocks:
        code_blocks.append({
            "language": block["language"] or "plaintext",
            "code": block["code"],
            "line": block["line"],
            "file": str(file_path)
        })

    return code_blocks


def _validate_code_snippets(docs_path: Path, project_path: Path, include_root_readme: bool = False, markdown_cache: MarkdownCache | None = None) -> list[dict[str, Any]]:
    """Extract and validate code snippets using TreeSitter."""
    issues = []
    validator = CodeValidator()
    markdown_files = find_markdown_files(
        docs_path,
        project_path=project_path,
        validate_boundaries=False,
        include_root_readme=include_root_readme
    )

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            code_blocks = _extract_code_blocks(content, md_file, markdown_cache)

            for block in code_blocks:
                # Normalize language names for TreeSitter
                language = block['language'].lower()
                if language == 'py':
                    language = 'python'
                elif language == 'js':
                    language = 'javascript'
                elif language == 'ts':
                    language = 'typescript'

                # Validate syntax using TreeSitter
                result = validator.validate_syntax(language, block['code'])

                if not result['valid'] and result['errors']:
                    for error in result['errors']:
                        issues.append({
                            "type": "syntax_error",
                            "severity": "warning",
                            "file": get_doc_relative_path(md_file, docs_path, project_path),
                            "line": block['line'] + error['line'] - 1,  # Adjust line number
                            "message": f"{error['message']} at line {error['line']}, column {error['column']}",
                            "language": block['language']
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


def _validate_code_syntax(docs_path: Path, project_path: Path, include_root_readme: bool = False) -> list[dict[str, Any]]:
    """Validate code example syntax using TreeSitter (semantic validation)."""
    issues = []
    markdown_files = find_markdown_files(
        docs_path,
        project_path=project_path,
        validate_boundaries=False,
        include_root_readme=include_root_readme
    )

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Use validation_helpers function
            file_issues = validate_code_examples(content, md_file, project_path, docs_path)
            issues.extend(file_issues)

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": get_doc_relative_path(md_file, docs_path, project_path),
                "line": 1,
                "message": f"Failed to read file: {e!s}"
            })

    return issues


def _validate_symbols(docs_path: Path, project_path: Path, include_root_readme: bool = False, symbol_index=None) -> list[dict[str, Any]]:
    """Validate that documented symbols exist in codebase."""
    issues = []
    markdown_files = find_markdown_files(
        docs_path,
        project_path=project_path,
        validate_boundaries=False,
        include_root_readme=include_root_readme
    )

    # Build symbol index once if not provided
    if symbol_index is None:
        try:
            indexer = SymbolIndexer()
            indexer.index_project(project_path)
            symbol_index = indexer.index
        except Exception as e:
            # TreeSitter not available or indexing failed
            print(f"Warning: Symbol indexing failed: {e}", file=sys.stderr)
            return []

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Use validation_helpers function
            file_issues = validate_documented_symbols(content, md_file, project_path, symbol_index, docs_path)
            issues.extend(file_issues)

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": get_doc_relative_path(md_file, docs_path, project_path),
                "line": 1,
                "message": f"Failed to read file: {e!s}"
            })

    return issues


def _format_validation_report(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Format validation report as structured data."""
    return {
        "total_issues": len(issues),
        "errors": len([i for i in issues if i['severity'] == 'error']),
        "warnings": len([i for i in issues if i['severity'] == 'warning']),
        "issues": issues
    }


def with_timeout(timeout_seconds):
    """Decorator to enforce timeout on async function execution (FR-021)."""
    def decorator(func):
        from functools import wraps

        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Use asyncio.wait_for for async timeout enforcement
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError as err:
                raise TimeoutError(
                    f"Operation exceeded timeout ({timeout_seconds}s)\n"
                    f"→ Consider processing fewer files or increasing timeout limit."
                ) from err
        return wrapper
    return decorator


def _validate_conventions(docs_path: Path, project_path: Path, conventions, include_root_readme: bool = False) -> list[dict[str, Any]]:
    """Validate documentation files against conventions.

    Args:
        docs_path: Path to documentation directory
        project_path: Path to project root
        conventions: DocumentationConventions object
        include_root_readme: Whether to include root README.md

    Returns:
        List of convention violations
    """
    issues = []
    markdown_files = find_markdown_files(
        docs_path,
        project_path=project_path,
        validate_boundaries=False,
        include_root_readme=include_root_readme
    )

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Validate against conventions
            violations = validate_against_conventions(
                content,
                conventions,
                get_doc_relative_path(md_file, docs_path, project_path)
            )

            # Convert violations to issue format
            for violation in violations:
                issues.append({
                    "type": "convention",
                    "severity": violation.get("severity", "warning"),
                    "file": violation.get("file", get_doc_relative_path(md_file, docs_path, project_path)),
                    "line": violation.get("line"),
                    "rule": violation.get("rule"),
                    "message": violation.get("message")
                })

        except Exception as e:
            print(f"Warning: Failed to validate conventions in {md_file}: {e}", file=sys.stderr)
            continue

    return issues


async def validate_docs(params: ValidateDocsInput) -> str | dict[str, Any]:
    """Validate documentation for broken links, missing assets, and code snippet issues.

    This tool performs comprehensive validation:
    1. Broken Links - Checks internal markdown and HTML links
    2. Asset Validation - Verifies images exist and have alt text
    3. Code Snippet Validation - Basic syntax checking for code blocks
    4. Code Syntax Validation - TreeSitter-based semantic validation (optional)
    5. Symbol Validation - Verify documented symbols exist in codebase (optional)

    Args:
        params (ValidateDocsInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - docs_path (Optional[str]): Relative path to docs directory
            - check_links (bool): Enable link validation (default: True)
            - check_assets (bool): Enable asset validation (default: True)
            - check_snippets (bool): Enable code snippet validation (default: True)
            - validate_code_syntax (bool): Enable TreeSitter syntax validation (default: False)
            - validate_symbols (bool): Validate documented symbols exist (default: False)
            - response_format (ResponseFormat): Output format (markdown or json)

    Returns:
        str: Validation report with all issues found

    Examples:
        - Use when: Preparing documentation for release
        - Use when: After making significant doc changes
        - Use when: Running CI/CD validation checks

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if docs_path specified but not found
        - Skips individual files that can't be read
    """
    try:
        project_path = safe_resolve(Path(params.project_path))

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Determine docs directory
        if params.docs_path:
            docs_path = project_path / params.docs_path
            if not docs_path.exists():
                return enforce_response_limit(f"Error: Documentation path does not exist: {docs_path}")
        else:
            docs_path = find_docs_directory(project_path)
            if not docs_path:
                return enforce_response_limit("Error: Could not find documentation directory. Please specify docs_path parameter.")

        if not docs_path.is_dir():
            return enforce_response_limit(f"Error: Documentation path is not a directory: {docs_path}")

        # Load config and conventions
        config = load_config(project_path)
        include_root_readme = config.get('include_root_readme', False) if config else False
        conventions = load_conventions(project_path)

        # Create markdown cache for performance (eliminates redundant parsing)
        markdown_cache = MarkdownCache()

        # Run validation checks
        all_issues = []

        # Check convention compliance if conventions exist
        if conventions:
            convention_issues = _validate_conventions(docs_path, project_path, conventions, include_root_readme)
            all_issues.extend(convention_issues)

        if params.check_links:
            link_issues = _check_broken_links(docs_path, project_path, include_root_readme, markdown_cache)
            all_issues.extend(link_issues)

        if params.check_assets:
            asset_issues = _validate_assets(docs_path, project_path, include_root_readme, markdown_cache)
            all_issues.extend(asset_issues)

        if params.check_snippets:
            snippet_issues = _validate_code_snippets(docs_path, project_path, include_root_readme, markdown_cache)
            all_issues.extend(snippet_issues)

        if params.validate_code_syntax:
            syntax_issues = _validate_code_syntax(docs_path, project_path, include_root_readme)
            all_issues.extend(syntax_issues)

        if params.validate_symbols:
            symbol_issues = _validate_symbols(docs_path, project_path, include_root_readme)
            all_issues.extend(symbol_issues)

        return enforce_response_limit(_format_validation_report(all_issues))

    except Exception as e:
        return enforce_response_limit(handle_error(e, "validate_docs"))
