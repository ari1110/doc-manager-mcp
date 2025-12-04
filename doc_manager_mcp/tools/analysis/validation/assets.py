"""Asset validation for documentation.

Task 2.3: Use asset_to_docs from dependencies.json for comprehensive asset tracking.
"""

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from doc_manager_mcp.schemas.baselines import DependenciesBaseline

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


def validate_external_assets(
    project_path: Path,
    dependencies: "dict[str, Any] | DependenciesBaseline | None" = None,
) -> list[dict[str, Any]]:
    """Validate external assets referenced in documentation.

    Task 2.3: Use asset_to_docs from dependencies.json to check external asset reachability.

    This function checks if external URLs (http/https) are reachable. Since this involves
    network requests, it's expensive and should be opt-in.

    Args:
        project_path: Path to project root
        dependencies: Pre-loaded dependencies.json data (optional)

    Returns:
        List of validation issues for unreachable external assets
    """
    issues = []

    # Load dependencies if not provided
    if dependencies is None:
        from doc_manager_mcp.tools._internal.dependencies import load_dependencies
        dependencies = load_dependencies(project_path, validate=False)

    if not dependencies:
        return issues

    # Get asset_to_docs mapping from dependencies
    asset_to_docs = dependencies.get("asset_to_docs", {}) if isinstance(dependencies, dict) else getattr(dependencies, "asset_to_docs", {})

    # Filter to external URLs only
    external_assets = {
        asset: docs for asset, docs in asset_to_docs.items()
        if asset.startswith(('http://', 'https://'))
    }

    if not external_assets:
        return issues

    # Check external URLs (with timeout to avoid hanging)
    import urllib.request
    import urllib.error

    for asset_url, doc_files in external_assets.items():
        try:
            # HEAD request with short timeout (don't download full content)
            req = urllib.request.Request(asset_url, method='HEAD')
            req.add_header('User-Agent', 'doc-manager-mcp/1.0 (external asset validator)')
            with urllib.request.urlopen(req, timeout=5) as response:  # noqa: S310
                if response.status >= 400:
                    for doc_file in doc_files:
                        issues.append({
                            "type": "external_asset_error",
                            "severity": "warning",
                            "file": doc_file,
                            "line": 1,
                            "message": f"External asset returned HTTP {response.status}: {asset_url}",
                            "asset_url": asset_url,
                        })
        except urllib.error.HTTPError as e:
            for doc_file in doc_files:
                issues.append({
                    "type": "external_asset_error",
                    "severity": "warning",
                    "file": doc_file,
                    "line": 1,
                    "message": f"External asset returned HTTP {e.code}: {asset_url}",
                    "asset_url": asset_url,
                })
        except urllib.error.URLError as e:
            for doc_file in doc_files:
                issues.append({
                    "type": "external_asset_unreachable",
                    "severity": "warning",
                    "file": doc_file,
                    "line": 1,
                    "message": f"External asset unreachable: {asset_url} ({e.reason})",
                    "asset_url": asset_url,
                })
        except Exception as e:
            for doc_file in doc_files:
                issues.append({
                    "type": "external_asset_error",
                    "severity": "warning",
                    "file": doc_file,
                    "line": 1,
                    "message": f"Failed to check external asset: {asset_url} ({e})",
                    "asset_url": asset_url,
                })

    return issues


def get_asset_coverage(
    project_path: Path,
    dependencies: "dict[str, Any] | DependenciesBaseline | None" = None,
) -> dict[str, Any]:
    """Get asset coverage metrics from dependencies.json.

    Args:
        project_path: Path to project root
        dependencies: Pre-loaded dependencies.json data (optional)

    Returns:
        Dict with asset coverage metrics
    """
    # Load dependencies if not provided
    if dependencies is None:
        from doc_manager_mcp.tools._internal.dependencies import load_dependencies
        dependencies = load_dependencies(project_path, validate=False)

    if not dependencies:
        return {
            "total_assets": 0,
            "local_assets": 0,
            "external_assets": 0,
            "docs_with_assets": 0,
        }

    asset_to_docs = dependencies.get("asset_to_docs", {}) if isinstance(dependencies, dict) else getattr(dependencies, "asset_to_docs", {})

    local_assets = [a for a in asset_to_docs if not a.startswith(('http://', 'https://'))]
    external_assets = [a for a in asset_to_docs if a.startswith(('http://', 'https://'))]

    # Count unique docs with assets
    docs_with_assets = set()
    for doc_list in asset_to_docs.values():
        docs_with_assets.update(doc_list)

    return {
        "total_assets": len(asset_to_docs),
        "local_assets": len(local_assets),
        "external_assets": len(external_assets),
        "docs_with_assets": len(docs_with_assets),
    }
