"""Pattern matching utilities for file exclusion.

This module provides utilities for matching file paths against glob patterns,
supporting complex patterns like **/ prefixes and /** suffixes.

Also provides shared exclude pattern building logic to eliminate duplication
across init, update_baseline, and detect_changes tools.
"""

import fnmatch
from pathlib import Path


def build_exclude_patterns(project_path: Path) -> tuple[list[str], object | None]:
    """Build exclude patterns from config, gitignore, and defaults.

    Priority order: user patterns > gitignore > default patterns

    User patterns are checked first (highest priority), then gitignore patterns
    (if enabled), then built-in defaults (lowest priority).

    Args:
        project_path: Project root directory

    Returns:
        Tuple of (exclude_patterns list, gitignore_spec object or None)
    """
    from doc_manager_mcp.constants import DEFAULT_EXCLUDE_PATTERNS
    from doc_manager_mcp.core import load_config, parse_gitignore

    # Load config
    config = load_config(project_path)
    user_excludes = config.get("exclude", []) if config else []
    use_gitignore = config.get("use_gitignore", False) if config else False

    # Build exclude patterns with correct priority
    # User patterns are checked first (highest priority)
    exclude_patterns = []
    exclude_patterns.extend(user_excludes)

    # Parse .gitignore if enabled (middle priority)
    gitignore_spec = None
    if use_gitignore:
        gitignore_spec = parse_gitignore(project_path)

    # Built-in defaults added last (lowest priority)
    exclude_patterns.extend(DEFAULT_EXCLUDE_PATTERNS)

    return exclude_patterns, gitignore_spec


def matches_exclude_pattern(path: str, exclude_patterns: list[str]) -> bool:
    """Check if a path matches any of the exclude patterns.

    Args:
        path: Relative path to check (string)
        exclude_patterns: List of glob patterns (e.g., ["**/node_modules", "**/*.log"])

    Returns:
        True if path should be excluded, False otherwise
    """
    # Normalize path separators
    normalized_path = str(Path(path)).replace('\\', '/')

    for pattern in exclude_patterns:
        # Normalize pattern separators
        normalized_pattern = pattern.replace('\\', '/')

        # Handle **/ prefix (matches any depth)
        if normalized_pattern.startswith('**/'):
            pattern_suffix = normalized_pattern[3:]  # Remove **/
            # Check if pattern matches the full path or any part
            if fnmatch.fnmatch(normalized_path, '*/' + pattern_suffix) or \
               fnmatch.fnmatch(normalized_path, pattern_suffix):
                return True
            # Check if any component matches
            parts = normalized_path.split('/')
            for i, _part in enumerate(parts):
                remaining = '/'.join(parts[i:])
                if fnmatch.fnmatch(remaining, pattern_suffix):
                    return True
        # Handle /** suffix (matches directory and contents)
        elif normalized_pattern.endswith('/**'):
            dir_pattern = normalized_pattern[:-3]  # Remove /**
            if normalized_path.startswith(dir_pattern + '/') or normalized_path == dir_pattern:
                return True
        # Regular pattern matching
        else:
            if fnmatch.fnmatch(normalized_path, normalized_pattern):
                return True

    return False
