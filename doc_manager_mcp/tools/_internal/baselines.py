"""Baseline loading utilities for doc-manager.

This module provides typed, validated access to baseline files:
- repo-baseline.json: File checksums and project metadata
- symbol-baseline.json: Code symbols (via indexing.analysis.semantic_diff)
- dependencies.json: Code-to-doc mappings (via .dependencies module)
"""

import json
from pathlib import Path
from typing import Any

from doc_manager_mcp.schemas.baselines import RepoBaseline


def load_repo_baseline(
    project_path: Path,
    validate: bool = True,
    check_version: bool = False,
    required_version: str = "1.0.0",
) -> RepoBaseline | dict[str, Any] | None:
    """Load repo-baseline.json with optional schema validation.

    Args:
        project_path: Path to project root
        validate: Whether to validate against RepoBaseline schema (default True)
        check_version: Whether to verify baseline version compatibility (Task 1.6)
        required_version: Minimum required version for compatibility check

    Returns:
        RepoBaseline model if validate=True, raw dict if validate=False,
        or None if file doesn't exist or version incompatible (when check_version=True)

    Raises:
        pydantic.ValidationError: If validate=True and data is invalid
        json.JSONDecodeError: If file contains invalid JSON

    Example:
        >>> baseline = load_repo_baseline(project_path)
        >>> if baseline:
        ...     print(f"Project: {baseline.repo_name}")
        ...     print(f"Files: {baseline.file_count}")
        ...     print(f"Language: {baseline.language}")
    """
    baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"

    if not baseline_path.exists():
        return None

    with open(baseline_path, encoding="utf-8") as f:
        data = json.load(f)

    # Task 1.6: Check version compatibility if requested
    if check_version:
        is_compatible, actual_version = check_baseline_compatibility(project_path, required_version)
        if not is_compatible:
            import sys
            print(
                f"Warning: Baseline version {actual_version} is older than required {required_version}. "
                "Consider running docmgr_update_baseline to upgrade.",
                file=sys.stderr
            )

    if validate:
        return RepoBaseline.model_validate(data)

    return data


def get_baseline_version(project_path: Path) -> str | None:
    """Get the schema version from repo-baseline.json.

    Used for schema compatibility checks before loading.

    Args:
        project_path: Path to project root

    Returns:
        Version string (e.g., "1.0.0") or None if file doesn't exist
    """
    baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"

    if not baseline_path.exists():
        return None

    try:
        with open(baseline_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("version")
    except (json.JSONDecodeError, OSError):
        return None


def check_baseline_compatibility(project_path: Path, required_version: str = "1.0.0") -> tuple[bool, str | None]:
    """Check if baseline version is compatible with required version.

    Args:
        project_path: Path to project root
        required_version: Minimum required version (default "1.0.0")

    Returns:
        Tuple of (is_compatible, actual_version)
        - is_compatible: True if baseline version >= required_version
        - actual_version: The actual version found, or None if no baseline
    """
    actual_version = get_baseline_version(project_path)

    if actual_version is None:
        return (False, None)

    # Simple semver comparison (major.minor.patch)
    try:
        actual_parts = [int(p) for p in actual_version.split(".")]
        required_parts = [int(p) for p in required_version.split(".")]

        # Pad to equal length
        while len(actual_parts) < len(required_parts):
            actual_parts.append(0)
        while len(required_parts) < len(actual_parts):
            required_parts.append(0)

        is_compatible = actual_parts >= required_parts
        return (is_compatible, actual_version)
    except (ValueError, AttributeError):
        # If version parsing fails, assume compatible
        return (True, actual_version)
