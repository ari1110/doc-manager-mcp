"""Documentation validation tools for doc-manager."""

import asyncio
import json
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    calculate_checksum,
    enforce_response_limit,
    find_docs_directory,
    find_markdown_files,
    handle_error,
    load_config,
    load_conventions,
    safe_resolve,
)
from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.models import ValidateDocsInput
from doc_manager_mcp.tools._internal.baselines import load_repo_baseline
from doc_manager_mcp.tools._internal.dependencies import load_dependencies

from .assets import validate_assets, validate_external_assets
from .conventions import validate_conventions
from .links import check_broken_links
from .references import validate_stale_references
from .snippets import validate_code_snippets
from .symbols import validate_symbols
from .syntax import validate_code_syntax


def _load_repo_baseline(baseline_path_str: str) -> dict[str, Any] | None:
    """Load repository baseline from disk.

    Args:
        baseline_path_str: String path to baseline file

    Returns:
        Baseline dict or None if not found

    Note:
        Cache was removed to prevent stale data issues across operations.
    """
    baseline_path = Path(baseline_path_str)
    if not baseline_path.exists():
        return None

    try:
        return json.loads(baseline_path.read_text())
    except Exception:
        return None


def _detect_changed_docs(
    docs_path: Path,
    project_path: Path,
    include_root_readme: bool
) -> list[Path] | None:
    """Detect documentation files that changed since last baseline.

    Args:
        docs_path: Path to documentation directory
        project_path: Project root path
        include_root_readme: Whether to include root README.md

    Returns:
        List of changed file paths, or None if baseline doesn't exist
    """
    baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"

    # Load baseline using cached function
    baseline = _load_repo_baseline(str(baseline_path))
    if baseline is None:
        return None

    try:
        baseline_checksums = baseline.get("files", {})

        # Get all current markdown files
        all_docs = find_markdown_files(
            docs_path,
            project_path=project_path,
            validate_boundaries=False,
            include_root_readme=include_root_readme
        )

        # Filter to only changed files
        changed_docs = []
        for doc_file in all_docs:
            relative_path = str(doc_file.relative_to(project_path)).replace('\\', '/')

            # File is changed if:
            # 1. Not in baseline (new file)
            # 2. Checksum differs (modified file)
            if relative_path not in baseline_checksums:
                changed_docs.append(doc_file)
            else:
                current_checksum = calculate_checksum(doc_file)
                if current_checksum != baseline_checksums[relative_path]:
                    changed_docs.append(doc_file)

        return changed_docs

    except Exception:
        # If we can't read baseline, fall back to validating all files
        return None


def _format_validation_report(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Format validation report as structured data."""
    return {
        "total_issues": len(issues),
        "errors": len([i for i in issues if i['severity'] == 'error']),
        "warnings": len([i for i in issues if i['severity'] == 'warning']),
        "issues": issues
    }


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

        # Task 1.4 & 1.5: Load repo baseline for language and docs_exist
        repo_baseline_data = load_repo_baseline(project_path, validate=False)
        primary_language = repo_baseline_data.get("language") if isinstance(repo_baseline_data, dict) else None
        docs_exist = repo_baseline_data.get("docs_exist", True) if isinstance(repo_baseline_data, dict) else True

        # Task 1.5: Early exit if docs_exist=false in baseline
        if not docs_exist:
            return enforce_response_limit({
                "total_issues": 0,
                "errors": 0,
                "warnings": 0,
                "issues": [],
                "note": "No documentation found. Baseline indicates docs_exist=false."
            })

        # Determine which files to validate (incremental vs full)
        markdown_files = None
        if params.incremental:
            markdown_files = _detect_changed_docs(docs_path, project_path, include_root_readme)
            if markdown_files is not None and len(markdown_files) == 0:
                # No changes detected - return empty report
                return enforce_response_limit(_format_validation_report([]))

        # Create markdown cache for performance (eliminates redundant parsing)
        markdown_cache = MarkdownCache()

        # Run validation checks in parallel (2-3x faster, 5-10x in incremental mode)
        validators = []

        # Check convention compliance if conventions exist
        if conventions:
            validators.append(
                asyncio.to_thread(validate_conventions, docs_path, project_path, conventions, include_root_readme, markdown_files)
            )

        if params.check_links:
            validators.append(
                asyncio.to_thread(check_broken_links, docs_path, project_path, include_root_readme, markdown_cache, markdown_files)
            )

        if params.check_assets:
            validators.append(
                asyncio.to_thread(validate_assets, docs_path, project_path, include_root_readme, markdown_cache, markdown_files)
            )

        if params.check_snippets:
            validators.append(
                # Task 1.4: Pass primary_language for language-aware validation
                asyncio.to_thread(validate_code_snippets, docs_path, project_path, include_root_readme, markdown_cache, markdown_files, primary_language)
            )

        if params.validate_code_syntax:
            validators.append(
                asyncio.to_thread(validate_code_syntax, docs_path, project_path, include_root_readme, markdown_files)
            )

        if params.validate_symbols:
            validators.append(
                asyncio.to_thread(validate_symbols, docs_path, project_path, include_root_readme, None, markdown_files)
            )

        # Task 2.2: Check for stale references using dependencies.json
        dependencies_data = None
        if getattr(params, 'check_stale_references', True) or getattr(params, 'check_external_assets', False):
            dependencies_data = load_dependencies(project_path, validate=False)

        if getattr(params, 'check_stale_references', True) and dependencies_data:
            validators.append(
                asyncio.to_thread(validate_stale_references, project_path, dependencies_data)  # type: ignore[arg-type]
            )

        # Task 2.3: Check external asset URLs for reachability (opt-in, expensive)
        if getattr(params, 'check_external_assets', False) and dependencies_data:
            validators.append(
                asyncio.to_thread(validate_external_assets, project_path, dependencies_data)  # type: ignore[arg-type]
            )

        # Run all validators concurrently
        results = await asyncio.gather(*validators) if validators else []

        # Aggregate all issues
        all_issues = []
        for issues in results:
            all_issues.extend(issues)

        return enforce_response_limit(_format_validation_report(all_issues))

    except Exception as e:
        return enforce_response_limit(handle_error(e, "validate_docs"))
