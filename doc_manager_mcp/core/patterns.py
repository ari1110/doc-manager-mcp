"""Pattern matching utilities for file exclusion.

This module provides utilities for matching file paths against glob patterns,
supporting complex patterns like **/ prefixes and /** suffixes.

Also provides shared exclude pattern building logic to eliminate duplication
across init, update_baseline, and detect_changes tools.
"""

import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathspec


def build_exclude_patterns(project_path: Path) -> tuple[list[str], "pathspec.PathSpec | None"]:
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


# File categorization patterns for detect_changes
FILE_CATEGORY_PATTERNS = {
    "cli": {
        "path_patterns": ["cmd/", "/cmd/"],
        "description": "CLI and command-line tool changes"
    },
    "api": {
        "path_patterns": ["api/", "internal/", "pkg/", "lib/", "src/"],
        "description": "API and library code changes"
    },
    "config": {
        "extensions": [".yml", ".yaml", ".toml", ".json", ".ini", ".conf"],
        "description": "Configuration file changes"
    },
    "documentation": {
        "extensions": [".md", ".rst", ".txt"],
        "path_patterns": ["/docs/", "/documentation/"],
        "description": "Documentation changes"
    },
    "asset": {
        "extensions": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".pdf", ".mp4", ".webm", ".mov"],
        "description": "Asset and media file changes"
    },
    "dependency": {
        "files": ["package.json", "go.mod", "requirements.txt", "cargo.toml", "pom.xml", "build.gradle"],
        "description": "Dependency and package manifest changes"
    },
    "test": {
        "path_patterns": ["test_", "_test.", "test/", "tests/", "spec/", "__tests__/"],
        "description": "Test code changes"
    },
    "infrastructure": {
        "path_patterns": [".github/", ".gitlab/", "docker", "Dockerfile", ".ci/", "deploy/"],
        "description": "Infrastructure and CI/CD changes"
    }
}


def categorize_file_change(file_path: str) -> str:
    """Categorize the scope of a code change based on configurable patterns.

    Args:
        file_path: Relative file path to categorize

    Returns:
        Category string (cli, api, config, documentation, asset, dependency, test, infrastructure, other)
    """
    file_lower = file_path.lower()
    normalized_path = file_path.replace('\\', '/')

    # Check each category in priority order
    for category, config in FILE_CATEGORY_PATTERNS.items():
        # Check path patterns (for directories and file name patterns)
        if "path_patterns" in config:
            for pattern in config["path_patterns"]:
                if normalized_path.startswith(pattern) or pattern in normalized_path:
                    return category

        # Check file extensions
        if "extensions" in config:
            if any(file_lower.endswith(ext) for ext in config["extensions"]):
                return category

        # Check exact file names
        if "files" in config:
            if any(file_name in file_lower for file_name in config["files"]):
                return category

    return "other"
