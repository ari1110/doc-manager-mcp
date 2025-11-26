"""Shared file scanning logic for doc-manager.

This module consolidates duplicate file scanning code across init, update_baseline,
and detect_changes tools (~120 lines of duplication).

Provides unified file scanning with:
- Exclude pattern handling (user → gitignore → defaults)
- Path validation and security checks
- File categorization
- Configurable scanning methods (walk vs rglob)
"""

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from doc_manager_mcp.constants import MAX_FILES
from doc_manager_mcp.core import (
    matches_exclude_pattern,
    validate_path_boundary,
)
from doc_manager_mcp.core.patterns import build_exclude_patterns

if TYPE_CHECKING:
    import pathspec


def scan_project_files(
    project_path: Path,
    *,
    exclude_patterns: list[str] | None = None,
    gitignore_spec: "pathspec.PathSpec | None" = None,
    max_files: int = MAX_FILES,
    validate_boundaries: bool = True,
    use_walk: bool = False
) -> Iterator[Path]:
    """Scan project files with exclusion and validation.

    Args:
        project_path: Project root directory
        exclude_patterns: List of exclude patterns (if None, builds from config)
        gitignore_spec: Gitignore spec object (if None, builds from config)
        max_files: Maximum number of files to scan
        validate_boundaries: Whether to validate path boundaries (security check)
        use_walk: Use walk() instead of rglob() for scanning

    Yields:
        Path objects for files that pass all filters

    Raises:
        ValueError: If file count exceeds max_files
    """
    # Build exclude patterns if not provided
    if exclude_patterns is None:
        exclude_patterns, gitignore_spec = build_exclude_patterns(project_path)
    elif gitignore_spec is None:
        # Only build gitignore if patterns were provided but gitignore wasn't
        _, gitignore_spec = build_exclude_patterns(project_path)

    file_count = 0

    # Choose scanning method
    if use_walk:
        # Use walk() - better for deep directory structures
        file_iterator = _walk_files(project_path)
    else:
        # Use rglob() - simpler, works well for most projects
        file_iterator = project_path.rglob("*")

    for file_path in file_iterator:
        # Check file count limit
        if file_count >= max_files:
            raise ValueError(
                f"File count limit exceeded (maximum: {max_files:,} files)\n"
                f"→ Consider processing a smaller directory or increasing the limit."
            )

        # Only process files (not directories)
        if not file_path.is_file():
            continue

        # Skip hidden files/directories (files with parts starting with '.')
        if any(part.startswith('.') for part in file_path.parts):
            continue

        # Validate path boundary and check for malicious symlinks
        if validate_boundaries:
            try:
                _ = validate_path_boundary(file_path, project_path)
            except ValueError:
                # Skip files that escape project boundary or malicious symlinks
                continue

        # Get relative path for pattern matching
        relative_path = str(file_path.relative_to(project_path)).replace('\\', '/')

        # Skip if matches exclude patterns
        if matches_exclude_pattern(relative_path, exclude_patterns):
            continue

        # Skip if matches gitignore patterns
        if gitignore_spec and gitignore_spec.match_file(relative_path):
            continue

        # File passed all filters
        yield file_path
        file_count += 1


def _walk_files(project_path: Path) -> Iterator[Path]:
    """Walk directory tree using Path.walk() (Python 3.12+).

    Args:
        project_path: Root directory to walk

    Yields:
        Path objects for all files in the tree
    """
    for root, _dirs, files in project_path.walk():
        for file in files:
            yield root / file


def categorize_file(file_path: Path) -> str:
    """Categorize a file by its type/purpose.

    Args:
        file_path: Path to file

    Returns:
        Category string: "code", "docs", "config", "assets", or "other"
    """
    suffix = file_path.suffix.lower()
    name = file_path.name.lower()

    # Code files
    if suffix in {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.hpp'}:
        return "code"

    # Documentation
    if suffix in {'.md', '.rst', '.txt', '.adoc'} or 'readme' in name or 'changelog' in name:
        return "docs"

    # Configuration
    if suffix in {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'} or name in {'dockerfile', 'makefile'}:
        return "config"

    # Assets
    if suffix in {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.pdf'}:
        return "assets"

    return "other"


def scan_and_categorize(
    project_path: Path,
    **scan_kwargs
) -> dict[str, list[Path]]:
    """Scan project files and categorize them by type.

    Args:
        project_path: Project root directory
        **scan_kwargs: Additional arguments passed to scan_project_files()

    Returns:
        Dict mapping category names to lists of Paths:
        {"code": [], "docs": [], "config": [], "assets": [], "other": []}
    """
    categorized = {
        "code": [],
        "docs": [],
        "config": [],
        "assets": [],
        "other": []
    }

    for file_path in scan_project_files(project_path, **scan_kwargs):
        category = categorize_file(file_path)
        categorized[category].append(file_path)

    return categorized
