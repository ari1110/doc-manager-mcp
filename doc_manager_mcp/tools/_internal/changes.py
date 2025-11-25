"""Change mapping tools for doc-manager."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from doc_manager_mcp.constants import (
    DEFAULT_EXCLUDE_PATTERNS,
    MAX_FILES,
    OPERATION_TIMEOUT,
    ChangeDetectionMode,
)
from doc_manager_mcp.core import (
    calculate_checksum,
    enforce_response_limit,
    handle_error,
    load_config,
    matches_exclude_pattern,
    run_git_command,
    validate_path_boundary,
)
from doc_manager_mcp.indexing.analysis.semantic_diff import (
    SemanticChange,
    compare_symbols,
    load_symbol_baseline,
    save_symbol_baseline,
)
from doc_manager_mcp.indexing.path_index import build_path_index
from doc_manager_mcp.indexing.analysis.tree_sitter import SymbolIndexer
from doc_manager_mcp.models import MapChangesInput


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
    from doc_manager_mcp.core.file_scanner import scan_project_files
    from doc_manager_mcp.core.patterns import build_exclude_patterns

    changed_files = []
    baseline_checksums = baseline.get("files", {})

    # Build exclude patterns for deleted file checks
    exclude_patterns, gitignore_spec = build_exclude_patterns(project_path)

    # Check existing files for changes using shared scanner
    for file_path in scan_project_files(project_path, max_files=MAX_FILES):
        relative_path = str(file_path.relative_to(project_path)).replace('\\', '/')

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

    # Check for deleted files
    for baseline_file in baseline_checksums.keys():
        # Skip deleted files if they match exclude patterns (FR-027)
        if matches_exclude_pattern(baseline_file, exclude_patterns):
            continue

        # Skip if matches gitignore patterns
        if gitignore_spec and gitignore_spec.match_file(baseline_file):
            continue

        file_path = project_path / baseline_file
        if not file_path.exists():
            changed_files.append({
                "file": baseline_file,
                "change_type": "deleted"
            })

    return changed_files


async def _get_changed_files_from_git(project_path: Path, since_commit: str) -> list[dict[str, str]]:
    """Get changed files from git diff."""
    changed_files = []

    # Load config to get exclude patterns (FR-027)
    config = load_config(project_path)
    user_excludes = config.get("exclude", []) if config else []
    use_gitignore = config.get("use_gitignore", False) if config else False

    # Build exclude patterns with correct priority:
    # Priority order: user > gitignore > defaults
    # User patterns are checked first (highest priority)
    exclude_patterns = []
    exclude_patterns.extend(user_excludes)

    # Parse .gitignore if enabled (middle priority)
    gitignore_spec = None
    if use_gitignore:
        from doc_manager_mcp.core import parse_gitignore
        gitignore_spec = parse_gitignore(project_path)

    # Built-in defaults added last (lowest priority)
    exclude_patterns.extend(DEFAULT_EXCLUDE_PATTERNS)

    # Get list of changed files
    output = await run_git_command(project_path, "diff", "--name-status", since_commit, "HEAD")

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

        # Skip if matches gitignore patterns
        if gitignore_spec and gitignore_spec.match_file(file_path):
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
    if any(x in normalized_path for x in ["api/", "internal/", "pkg/", "lib/", "src/"]):
        return "api"

    # Configuration changes
    if any(file_lower.endswith(ext) for ext in [".yml", ".yaml", ".toml", ".json", ".ini", ".conf"]):
        return "config"

    # Documentation changes
    if file_lower.endswith((".md", ".rst", ".txt")) or "/docs/" in normalized_path or "/documentation/" in normalized_path:
        return "documentation"

    # Asset changes (images, media files commonly referenced in docs)
    if any(file_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".pdf", ".mp4", ".webm", ".mov"]):
        return "asset"

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
    """Map changed files to affected documentation using configurable doc_mappings.

    Loads doc_mappings from .doc-manager.yml config. If not configured, falls back
    to default paths in docs/ directory. Supports non-standard layouts like
    documentation/, wiki/, _docs/, etc.

    Uses PathIndex for O(1) existence checks instead of file system access (2-3x faster).
    """
    affected_docs = {}  # Use dict to deduplicate

    # Load config and get doc_mappings
    config = load_config(project_path)
    docs_path = config.get("docs_path", "docs") if config else "docs"

    # Build path index once for O(1) lookups (instead of repeated file system checks)
    docs_root = project_path / docs_path
    path_index = build_path_index(docs_root, project_path) if docs_root.exists() else None

    # Start with default paths
    doc_mappings = {
        "cli": f"{docs_path}/reference/command-reference.md",
        "api": f"{docs_path}/reference/api.md",
        "config": f"{docs_path}/reference/configuration.md",
        "dependency": f"{docs_path}/getting-started/installation.md",
        "infrastructure": f"{docs_path}/development/ci-cd.md",
    }

    # Override with user-configured mappings (supports partial configs)
    if config and config.get("doc_mappings"):
        doc_mappings.update(config["doc_mappings"])

    for change in changed_files:
        file_path = change["file"]
        category = _categorize_change(file_path)

        # Skip if it's already a documentation change
        if category == "documentation":
            continue

        # Map based on category using configured paths
        if category == "cli":
            primary_doc = doc_mappings.get("cli")
            if primary_doc:
                _add_affected_doc(
                    affected_docs,
                    primary_doc,
                    f"CLI implementation changed: {file_path}",
                    "high",
                    file_path
                )

            # Secondary docs (workflows and README) - use defaults if not in config
            workflows_doc = doc_mappings.get("workflows") or f"{docs_path}/guides/basic-workflows.md"
            _add_affected_doc(
                affected_docs,
                workflows_doc,
                f"CLI workflows may need updates due to: {file_path}",
                "medium",
                file_path
            )

            readme_doc = doc_mappings.get("readme") or "README.md"
            _add_affected_doc(
                affected_docs,
                readme_doc,
                f"Update examples if this affects primary commands: {file_path}",
                "medium",
                file_path
            )

        elif category == "api":
            primary_doc = doc_mappings.get("api")
            if primary_doc:
                _add_affected_doc(
                    affected_docs,
                    primary_doc,
                    f"API/library changed: {file_path}",
                    "high",
                    file_path
                )

            # If internal/ changed, also flag architecture doc
            if "internal/" in file_path:
                arch_doc = doc_mappings.get("architecture") or f"{docs_path}/reference/architecture.md"
                _add_affected_doc(
                    affected_docs,
                    arch_doc,
                    f"Internal architecture may have changed: {file_path}",
                    "medium",
                    file_path
                )

        elif category == "config":
            primary_doc = doc_mappings.get("config")
            if primary_doc:
                _add_affected_doc(
                    affected_docs,
                    primary_doc,
                    f"Configuration schema changed: {file_path}",
                    "high",
                    file_path
                )

            # Config changes may also affect installation docs
            install_doc = doc_mappings.get("dependency") or f"{docs_path}/getting-started/installation.md"
            _add_affected_doc(
                affected_docs,
                install_doc,
                f"Configuration examples may need updates: {file_path}",
                "medium",
                file_path
            )

        elif category == "dependency":
            primary_doc = doc_mappings.get("dependency")
            if primary_doc:
                _add_affected_doc(
                    affected_docs,
                    primary_doc,
                    f"Dependencies changed: {file_path}",
                    "high",
                    file_path
                )

            # Dependency changes may affect contributing guide
            contrib_doc = doc_mappings.get("contributing") or f"{docs_path}/development/contributing.md"
            _add_affected_doc(
                affected_docs,
                contrib_doc,
                f"Development setup may have changed: {file_path}",
                "medium",
                file_path
            )

        elif category == "infrastructure":
            primary_doc = doc_mappings.get("infrastructure")
            if primary_doc:
                _add_affected_doc(
                    affected_docs,
                    primary_doc,
                    f"CI/CD configuration changed: {file_path}",
                    "low",
                    file_path
                )

    # Convert dict to list and check which docs actually exist
    # Use path index for O(1) existence checks instead of file system access
    result = []
    for doc_path, info in affected_docs.items():
        # Use path index if available, otherwise fall back to file system check
        if path_index:
            exists = path_index.exists(doc_path, project_path)
        else:
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


def _get_semantic_changes(project_path: Path) -> list[SemanticChange]:
    """Detect semantic code changes using TreeSitter (lazy loading).

    Compares current codebase symbols against stored baseline to detect:
    - Added/removed functions, classes, methods
    - Signature changes (breaking vs non-breaking)
    - Implementation changes

    Returns empty list if baseline doesn't exist or errors occur.
    """
    try:
        # Load or create symbol baseline (lazy)
        baseline_path = project_path / ".doc-manager" / "memory" / "symbol-baseline.json"
        old_symbols = load_symbol_baseline(baseline_path)

        # Index current codebase
        indexer = SymbolIndexer()
        new_symbols = indexer.index_project(project_path)

        # First run: create baseline and return empty changes
        if old_symbols is None:
            print("Creating symbol baseline for first semantic diff...", file=sys.stderr)
            save_symbol_baseline(baseline_path, new_symbols)
            return []

        # Compare and detect changes
        semantic_changes = compare_symbols(old_symbols, new_symbols)

        # Update baseline with current symbols
        save_symbol_baseline(baseline_path, new_symbols)

        return semantic_changes

    except Exception as e:
        print(f"Warning: Semantic diff failed: {e}", file=sys.stderr)
        return []


def _format_changes_report(changed_files: list[dict[str, str]], affected_docs: list[dict[str, Any]],
                           baseline_info: dict | None = None, semantic_changes: list[SemanticChange] | None = None) -> dict[str, Any]:
    """Format change mapping report."""
    return {
        "analyzed_at": datetime.now().isoformat(),
        "baseline_commit": baseline_info.get("git_commit") if baseline_info else None,
        "baseline_created": baseline_info.get("timestamp") if baseline_info else None,
        "changes_detected": len(changed_files) > 0,
        "total_changes": len(changed_files),
        "changed_files": changed_files,
        "affected_documentation": affected_docs,
        "semantic_changes": semantic_changes or []
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
            # Use git diff (since_commit is validated as required by model_validator)
            assert params.since_commit is not None, "since_commit required for git_diff mode"
            changed_files = await _get_changed_files_from_git(project_path, params.since_commit)
            baseline_info = {"git_commit": params.since_commit}
        else:
            # Use checksum comparison from memory (default: CHECKSUM mode)
            baseline = _load_baseline(project_path)
            if not baseline:
                return enforce_response_limit(f"Error: No baseline found at {project_path}/.doc-manager/memory/repo-baseline.json. Run docmgr_initialize_memory first or use mode='git_diff' with since_commit parameter.")

            changed_files = _get_changed_files_from_checksums(project_path, baseline)
            baseline_info = baseline

        # Map changes to affected docs
        affected_docs = _map_to_affected_docs(changed_files, project_path)

        # Detect semantic changes if enabled (lazy loading)
        semantic_changes = []
        if params.include_semantic:
            semantic_changes = _get_semantic_changes(project_path)

        return _format_changes_report(changed_files, affected_docs, baseline_info, semantic_changes)

    except Exception as e:
        return enforce_response_limit(handle_error(e, "map_changes"))


async def map_changes(params: MapChangesInput) -> str | dict[str, Any]:
    """Map code changes to affected documentation.

    INTERNAL USE ONLY: This function is not exposed as an MCP tool in v2.0.0.
    Use docmgr_detect_changes or docmgr_sync instead, which provide the same functionality.

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
            - mode (ChangeDetectionMode): Detection mode - either:
                * 'checksum': Compare file hashes against memory baseline (default)
                * 'git_diff': Use git diff to detect changes (requires since_commit)
            - since_commit (Optional[str]): Git commit SHA to compare from (7-40 hex chars)
                * Required when mode='git_diff'
                * Ignored when mode='checksum'
                * Example: 'abc1234' or full SHA
                * Note: Does not accept git refs like 'HEAD~3' (security: prevents command injection)
            - response_format (ResponseFormat): Output format (markdown or json)

    Returns:
        str: Change mapping report with affected documentation

    Examples:
        Mode 1 - Checksum comparison (default):
            - Compares current files against .doc-manager/memory/repo-baseline.json
            - Run docmgr_initialize_memory first to create baseline
            - Use when: Tracking changes since last memory snapshot

        Mode 2 - Git diff:
            - Uses git diff to detect changes since specified commit
            - Requires since_commit parameter with actual SHA hash
            - Use when: Comparing against specific git commit

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if mode='checksum' and no baseline found
        - Returns error if mode='git_diff' and since_commit not provided
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
