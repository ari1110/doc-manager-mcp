"""Asset validation for documentation."""

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
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser


def extract_images(
    content: str,
    file_path: Path,
    markdown_cache: MarkdownCache | None = None
) -> list[dict[str, Any]]:
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


def validate_assets(
    docs_path: Path,
    project_path: Path,
    include_root_readme: bool = False,
    markdown_cache: MarkdownCache | None = None,
    markdown_files: list[Path] | None = None
) -> list[dict[str, Any]]:
    """Validate asset links and alt text."""
    issues = []
    if markdown_files is None:
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

            images = extract_images(content, md_file, markdown_cache)

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
