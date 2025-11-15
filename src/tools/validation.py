"""Documentation validation tools for doc-manager."""

from pathlib import Path
import re
import sys
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from ..models import ValidateDocsInput
from ..constants import ResponseFormat
from ..utils import find_docs_directory, handle_error, enforce_response_limit, safe_json_dumps


def _find_markdown_files(docs_path: Path) -> List[Path]:
    """Find all markdown files in documentation directory."""
    markdown_files = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        markdown_files.extend(docs_path.glob(pattern))
    return sorted(markdown_files)


def _extract_links(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """Extract all links from markdown content."""
    links = []

    # Markdown links: [text](url)
    markdown_link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    for match in re.finditer(markdown_link_pattern, content):
        link_text = match.group(1)
        link_url = match.group(2)
        line_num = content[:match.start()].count('\n') + 1
        links.append({
            "text": link_text,
            "url": link_url,
            "line": line_num,
            "file": str(file_path)
        })

    # HTML links: <a href="url">
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


def _check_internal_link(link_url: str, file_path: Path, docs_root: Path) -> Optional[str]:
    """Check if internal link is valid. Returns error message if broken."""
    # Skip external links and anchors
    if link_url.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
        return None

    # Handle anchor-only links (valid if they reference content in same file)
    if link_url.startswith('#'):
        return None

    # Remove anchor from URL
    url_without_anchor = link_url.split('#')[0]
    if not url_without_anchor:
        return None

    # Resolve relative path
    if url_without_anchor.startswith('/'):
        # Absolute path from docs root
        target = docs_root / url_without_anchor.lstrip('/')
    else:
        # Relative to current file
        target = file_path.parent / url_without_anchor

    # Normalize path
    try:
        target = target.resolve()
    except Exception as e:
        print(f"Warning: Failed to resolve link path {link_url}: {e}", file=sys.stderr)
        return f"Invalid path format: {link_url}"

    # Check if target exists
    if not target.exists():
        return f"Broken link: {link_url} (target not found)"

    return None


def _check_broken_links(docs_path: Path) -> List[Dict[str, Any]]:
    """Check for broken internal and external links."""
    issues = []
    markdown_files = _find_markdown_files(docs_path)

    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            links = _extract_links(content, md_file)

            for link in links:
                # Check internal links only
                error = _check_internal_link(link['url'], md_file, docs_path)
                if error:
                    issues.append({
                        "type": "broken_link",
                        "severity": "error",
                        "file": str(md_file.relative_to(docs_path)),
                        "line": link['line'],
                        "message": error,
                        "link_text": link['text'],
                        "link_url": link['url']
                    })

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": str(md_file.relative_to(docs_path)),
                "line": 0,
                "message": f"Failed to read file: {str(e)}"
            })

    return issues


def _extract_images(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """Extract all images from markdown content."""
    images = []

    # Markdown images: ![alt](src)
    md_image_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
    for match in re.finditer(md_image_pattern, content):
        alt_text = match.group(1)
        image_src = match.group(2)
        line_num = content[:match.start()].count('\n') + 1
        images.append({
            "alt": alt_text,
            "src": image_src,
            "line": line_num,
            "file": str(file_path)
        })

    # HTML images: <img src="..." alt="...">
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


def _validate_assets(docs_path: Path) -> List[Dict[str, Any]]:
    """Validate asset links and alt text."""
    issues = []
    markdown_files = _find_markdown_files(docs_path)

    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            images = _extract_images(content, md_file)

            for img in images:
                # Check for missing alt text
                if not img['alt'].strip():
                    issues.append({
                        "type": "missing_alt_text",
                        "severity": "warning",
                        "file": str(md_file.relative_to(docs_path)),
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
                        image_path = image_path.resolve()
                        if not image_path.exists():
                            issues.append({
                                "type": "missing_asset",
                                "severity": "error",
                                "file": str(md_file.relative_to(docs_path)),
                                "line": img['line'],
                                "message": f"Image file not found: {img['src']}",
                                "image_src": img['src']
                            })
                    except Exception as e:
                        print(f"Warning: Failed to resolve image path {img['src']}: {e}", file=sys.stderr)
                        issues.append({
                            "type": "invalid_asset_path",
                            "severity": "error",
                            "file": str(md_file.relative_to(docs_path)),
                            "line": img['line'],
                            "message": f"Invalid image path: {img['src']}",
                            "image_src": img['src']
                        })

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": str(md_file.relative_to(docs_path)),
                "line": 0,
                "message": f"Failed to read file: {str(e)}"
            })

    return issues


def _extract_code_blocks(content: str, file_path: Path) -> List[Dict[str, Any]]:
    """Extract code blocks from markdown content."""
    code_blocks = []

    # Fenced code blocks: ```lang\ncode\n```
    code_block_pattern = r'```(\w+)?\n(.*?)\n```'
    for match in re.finditer(code_block_pattern, content, re.DOTALL):
        language = match.group(1) or "plaintext"
        code = match.group(2)
        line_num = content[:match.start()].count('\n') + 1
        code_blocks.append({
            "language": language,
            "code": code,
            "line": line_num,
            "file": str(file_path)
        })

    return code_blocks


def _validate_code_snippets(docs_path: Path) -> List[Dict[str, Any]]:
    """Extract and validate code snippets."""
    issues = []
    markdown_files = _find_markdown_files(docs_path)

    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            code_blocks = _extract_code_blocks(content, md_file)

            for block in code_blocks:
                # Basic validation: check for common syntax errors
                if block['language'] in ['python', 'py']:
                    # Check for obvious Python syntax issues
                    code = block['code']

                    # Check for unmatched parentheses/brackets
                    if code.count('(') != code.count(')'):
                        issues.append({
                            "type": "syntax_error",
                            "severity": "warning",
                            "file": str(md_file.relative_to(docs_path)),
                            "line": block['line'],
                            "message": "Unmatched parentheses in Python code block",
                            "language": block['language']
                        })

                    if code.count('[') != code.count(']'):
                        issues.append({
                            "type": "syntax_error",
                            "severity": "warning",
                            "file": str(md_file.relative_to(docs_path)),
                            "line": block['line'],
                            "message": "Unmatched brackets in Python code block",
                            "language": block['language']
                        })

                    if code.count('{') != code.count('}'):
                        issues.append({
                            "type": "syntax_error",
                            "severity": "warning",
                            "file": str(md_file.relative_to(docs_path)),
                            "line": block['line'],
                            "message": "Unmatched braces in Python code block",
                            "language": block['language']
                        })

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": str(md_file.relative_to(docs_path)),
                "line": 0,
                "message": f"Failed to read file: {str(e)}"
            })

    return issues


def _format_validation_report(issues: List[Dict[str, Any]], response_format: ResponseFormat) -> str:
    """Format validation report as JSON or Markdown."""
    if response_format == ResponseFormat.JSON:
        return enforce_response_limit(safe_json_dumps({
            "total_issues": len(issues),
            "errors": len([i for i in issues if i['severity'] == 'error']),
            "warnings": len([i for i in issues if i['severity'] == 'warning']),
            "issues": issues
        }, indent=2))
    else:
        lines = ["# Documentation Validation Report", ""]

        errors = [i for i in issues if i['severity'] == 'error']
        warnings = [i for i in issues if i['severity'] == 'warning']

        lines.append(f"**Total Issues:** {len(issues)}")
        lines.append(f"- Errors: {len(errors)}")
        lines.append(f"- Warnings: {len(warnings)}")
        lines.append("")

        if not issues:
            lines.append("✓ No issues found! Documentation is valid.")
            lines.append("")
            lines.append("**Status:** Validation complete.")
            return enforce_response_limit("\n".join(lines))

        if errors:
            lines.append("## Errors")
            lines.append("")
            for issue in errors:
                lines.append(f"### {issue['file']}:{issue['line']}")
                lines.append(f"**Type:** {issue['type']}")
                lines.append(f"**Message:** {issue['message']}")
                lines.append("")

        if warnings:
            lines.append("## Warnings")
            lines.append("")
            for issue in warnings:
                lines.append(f"### {issue['file']}:{issue['line']}")
                lines.append(f"**Type:** {issue['type']}")
                lines.append(f"**Message:** {issue['message']}")
                lines.append("")

        return enforce_response_limit("\n".join(lines))


async def validate_docs(params: ValidateDocsInput) -> str:
    """Validate documentation for broken links, missing assets, and code snippet issues.

    This tool performs comprehensive validation:
    1. Broken Links - Checks internal markdown and HTML links
    2. Asset Validation - Verifies images exist and have alt text
    3. Code Snippet Validation - Basic syntax checking for code blocks

    Args:
        params (ValidateDocsInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - docs_path (Optional[str]): Relative path to docs directory
            - check_links (bool): Enable link validation (default: True)
            - check_assets (bool): Enable asset validation (default: True)
            - check_snippets (bool): Enable code snippet validation (default: True)
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
        project_path = Path(params.project_path).resolve()

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

        # Run validation checks
        all_issues = []

        if params.check_links:
            link_issues = _check_broken_links(docs_path)
            all_issues.extend(link_issues)

        if params.check_assets:
            asset_issues = _validate_assets(docs_path)
            all_issues.extend(asset_issues)

        if params.check_snippets:
            snippet_issues = _validate_code_snippets(docs_path)
            all_issues.extend(snippet_issues)

        return enforce_response_limit(_format_validation_report(all_issues, params.response_format))

    except Exception as e:
        return enforce_response_limit(handle_error(e, "validate_docs"))
