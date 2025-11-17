"""Change mapping tools for doc-manager."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ..constants import DEFAULT_EXCLUDE_PATTERNS, MAX_FILES, OPERATION_TIMEOUT, ChangeDetectionMode
from ..models import MapChangesInput
from ..utils import (
    calculate_checksum,
    enforce_response_limit,
    handle_error,
    load_config,
    matches_exclude_pattern,
    run_git_command,
    validate_path_boundary,
)


def _load_baseline(project_path: Path) -> dict[str, Any] | None:
    """Load baseline checksums from memory."""
    baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"
    if not baseline_path.exists():
        return None

    try:
        with open(baseline_path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load baseline from {baseline_path}: {e}", file=sys.stderr)
        return None


def _get_changed_files_from_checksums(project_path: Path, baseline: dict[str, Any]) -> list[dict[str, str]]:
    """Compare current checksums with baseline to find changed files."""
    changed_files = []
    baseline_checksums = baseline.get("files", {})

    # Load config to get exclude patterns (FR-027)
    config = load_config(project_path)
    user_excludes = config.get("exclude", []) if config else []
    # Merge default excludes with user excludes (defaults always applied)
    exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS) + user_excludes

    # Check existing files for changes
    file_count = 0
    for file_path in project_path.rglob("*"):
        if file_count >= MAX_FILES:
            raise ValueError(
                f"File count limit exceeded (maximum: {MAX_FILES:,} files)\n"
                f"→ Consider processing a smaller directory or increasing the limit."
            )

        if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
            # Validate path boundary and check for malicious symlinks (T029 - FR-028)
            try:
                _ = validate_path_boundary(file_path, project_path)
            except ValueError:
                # Skip files that escape project boundary or malicious symlinks
                continue

            relative_path = str(file_path.relative_to(project_path)).replace('\\', '/')

            # Skip if matches exclude patterns (FR-027)
            if matches_exclude_pattern(relative_path, exclude_patterns):
                continue

            current_checksum = calculate_checksum(file_path)
            baseline_checksum = baseline_checksums.get(relative_path)

            if baseline_checksum != current_checksum:
                if baseline_checksum:
                    changed_files.append({
                        "file": relative_path,
                        "change_type": "modified"
                    })
                else:
                    changed_files.append({
                        "file": relative_path,
                        "change_type": "added"
                    })

            file_count += 1

    # Check for deleted files
    for baseline_file in baseline_checksums.keys():
        # Skip deleted files if they match exclude patterns (FR-027)
        if matches_exclude_pattern(baseline_file, exclude_patterns):
            continue

        file_path = project_path / baseline_file
        if not file_path.exists():
            changed_files.append({
                "file": baseline_file,
                "change_type": "deleted"
            })

    return changed_files


def _get_changed_files_from_git(project_path: Path, since_commit: str) -> list[dict[str, str]]:
    """Get changed files from git diff."""
    changed_files = []

    # Load config to get exclude patterns (FR-027)
    config = load_config(project_path)
    user_excludes = config.get("exclude", []) if config else []
    # Merge default excludes with user excludes (defaults always applied)
    exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS) + user_excludes

    # Get list of changed files
    output = run_git_command(project_path, "diff", "--name-status", since_commit, "HEAD")

    if not output:
        return changed_files

    for line in output.split('\n'):
        if not line.strip():
            continue

        parts = line.split('\t')
        if len(parts) < 2:
            continue

        status = parts[0]
        file_path = parts[1]

        # Skip if matches exclude patterns (FR-027)
        if matches_exclude_pattern(file_path, exclude_patterns):
            continue

        if status.startswith('M'):
            change_type = "modified"
        elif status.startswith('A'):
            change_type = "added"
        elif status.startswith('D'):
            change_type = "deleted"
        elif status.startswith('R'):
            change_type = "renamed"
        else:
            change_type = "modified"

        changed_files.append({
            "file": file_path,
            "change_type": change_type
        })

    return changed_files


def _categorize_change(file_path: str) -> str:
    """Categorize the scope of a code change."""
    file_lower = file_path.lower()
    # Normalize path separators for consistent matching
    normalized_path = file_path.replace('\\', '/')

    # CLI/Command changes
    if normalized_path.startswith("cmd/") or "/cmd/" in normalized_path:
        return "cli"

    # API/Library changes
    if any(x in normalized_path for x in ["internal/", "pkg/", "lib/", "src/"]):
        return "api"

    # Configuration changes
    if any(file_lower.endswith(ext) for ext in [".yml", ".yaml", ".toml", ".json", ".ini", ".conf"]):
        return "config"

    # Documentation changes
    if file_lower.endswith((".md", ".rst", ".txt")) or "/docs/" in normalized_path or "/documentation/" in normalized_path:
        return "documentation"

    # Build/Dependency changes
    if any(x in file_lower for x in ["package.json", "go.mod", "requirements.txt", "cargo.toml", "pom.xml", "build.gradle"]):
        return "dependency"

    # Tests
    if any(x in file_lower for x in ["test_", "_test.", "test/", "tests/", "spec/", "__tests__/"]):
        return "test"

    # Infrastructure/Config
    if any(x in normalized_path for x in [".github/", ".gitlab/", "docker", "Dockerfile", ".ci/", "deploy/"]):
        return "infrastructure"

    return "other"


def _map_to_affected_docs(changed_files: list[dict[str, str]], project_path: Path) -> list[dict[str, Any]]:
    """Map changed files to affected documentation."""
    affected_docs = {}  # Use dict to deduplicate

    for change in changed_files:
        file_path = change["file"]
        category = _categorize_change(file_path)

        # Skip if it's already a documentation change
        if category == "documentation":
            continue

        # Map based on category
        if category == "cli":
            _add_affected_doc(
                affected_docs,
                "docs/reference/command-reference.md",
                f"CLI implementation changed: {file_path}",
                "high",
                file_path
            )
            _add_affected_doc(
                affected_docs,
                "docs/guides/basic-workflows.md",
                f"CLI workflows may need updates due to: {file_path}",
                "medium",
                file_path
            )
            _add_affected_doc(
                affected_docs,
                "README.md",
                f"Update examples if this affects primary commands: {file_path}",
                "medium",
                file_path
            )

        elif category == "api":
            _add_affected_doc(
                affected_docs,
                "docs/reference/api.md",
                f"API/library changed: {file_path}",
                "high",
                file_path
            )
            if "internal/" in file_path:
                _add_affected_doc(
                    affected_docs,
                    "docs/reference/architecture.md",
                    f"Internal architecture may have changed: {file_path}",
                    "medium",
                    file_path
                )

        elif category == "config":
            _add_affected_doc(
                affected_docs,
                "docs/reference/configuration.md",
                f"Configuration schema changed: {file_path}",
                "high",
                file_path
            )
            _add_affected_doc(
                affected_docs,
                "docs/getting-started/installation.md",
                f"Configuration examples may need updates: {file_path}",
                "medium",
                file_path
            )

        elif category == "dependency":
            _add_affected_doc(
                affected_docs,
                "docs/getting-started/installation.md",
                f"Dependencies changed: {file_path}",
                "high",
                file_path
            )
            _add_affected_doc(
                affected_docs,
                "docs/development/contributing.md",
                f"Development setup may have changed: {file_path}",
                "medium",
                file_path
            )

        elif category == "infrastructure":
            _add_affected_doc(
                affected_docs,
                "docs/development/ci-cd.md",
                f"CI/CD configuration changed: {file_path}",
                "low",
                file_path
            )

    # Convert dict to list and check which docs actually exist
    result = []
    for doc_path, info in affected_docs.items():
        doc_file = project_path / doc_path
        exists = doc_file.exists()

        result.append({
            "file": doc_path,
            "exists": exists,
            "reason": info["reason"],
            "priority": info["priority"],
            "affected_by": info["affected_by"]
        })

    return result


def _add_affected_doc(affected_docs: dict, doc_path: str, reason: str, priority: str, source_file: str):
    """Add or update affected documentation entry."""
    if doc_path not in affected_docs:
        affected_docs[doc_path] = {
            "reason": reason,
            "priority": priority,
            "affected_by": [source_file]
        }
    else:
        # Update with higher priority if needed
        if priority == "high" and affected_docs[doc_path]["priority"] != "high":
            affected_docs[doc_path]["priority"] = "high"

        # Add source file if not already listed
        if source_file not in affected_docs[doc_path]["affected_by"]:
            affected_docs[doc_path]["affected_by"].append(source_file)


def _format_changes_report(changed_files: list[dict[str, str]], affected_docs: list[dict[str, Any]],
                           baseline_info: dict | None = None) -> dict[str, Any]:
    """Format change mapping report."""
    return {
        "analyzed_at": datetime.now().isoformat(),
        "baseline_commit": baseline_info.get("git_commit") if baseline_info else None,
        "baseline_created": baseline_info.get("timestamp") if baseline_info else None,
        "changes_detected": len(changed_files) > 0,
        "total_changes": len(changed_files),
        "changed_files": changed_files,
        "affected_documentation": affected_docs
    }


async def _map_changes_impl(params: MapChangesInput) -> str | dict[str, Any]:
    """Implementation of map_changes without timeout."""
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        changed_files = []
        baseline_info = None

        if params.mode == ChangeDetectionMode.GIT_DIFF:
            # Use git diff
            since_commit = params.since_commit or "HEAD~1"
            changed_files = _get_changed_files_from_git(project_path, since_commit)
            baseline_info = {"git_commit": since_commit}
        else:
            # Use checksum comparison from memory (default: CHECKSUM mode)
            baseline = _load_baseline(project_path)
            if not baseline:
                return enforce_response_limit(f"Error: No baseline found at {project_path}/.doc-manager/memory/repo-baseline.json. Run docmgr_initialize_memory first or use mode='git_diff' with since_commit parameter.")

            changed_files = _get_changed_files_from_checksums(project_path, baseline)
            baseline_info = baseline

        # Map changes to affected docs
        affected_docs = _map_to_affected_docs(changed_files, project_path)

        return _format_changes_report(changed_files, affected_docs, baseline_info)

    except Exception as e:
        return enforce_response_limit(handle_error(e, "map_changes"))


async def map_changes(params: MapChangesInput) -> str | dict[str, Any]:
    """Map code changes to affected documentation.

    Compares current codebase state against baseline (from memory or git commit)
    and identifies which documentation files need updates based on code changes.

    Uses pattern-based mapping:
    - CLI changes → command reference, workflow guides
    - API changes → API reference, architecture docs
    - Config changes → configuration reference, installation docs
    - Dependency changes → installation guide, contributing guide

    Args:
        params (MapChangesInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - since_commit (Optional[str]): Git commit to compare from (uses memory baseline if not specified)
            - response_format (ResponseFormat): Output format (markdown or json)

    Returns:
        str: Change mapping report with affected documentation

    Examples:
        - Use when: After making code changes
        - Use when: Before updating documentation
        - Use when: In CI/CD to detect doc update needs

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if no baseline found and no commit specified
        - Returns empty change list if no changes detected
        - Raises TimeoutError if operation exceeds OPERATION_TIMEOUT (60s)
    """
    try:
        # Wrap the implementation with timeout enforcement (FR-021)
        result = await asyncio.wait_for(
            _map_changes_impl(params),
            timeout=OPERATION_TIMEOUT
        )
        return result
    except asyncio.TimeoutError as err:
        raise TimeoutError(
            f"Operation exceeded timeout ({OPERATION_TIMEOUT}s)\n"
            f"→ Consider processing fewer files or increasing timeout limit."
        ) from err
