"""Pure read-only change detection tool (T008).

Key difference from map_changes: NEVER writes to symbol-baseline.json
"""

from pathlib import Path
from typing import Any

from doc_manager_mcp.core import enforce_response_limit, handle_error
from doc_manager_mcp.models import DocmgrDetectChangesInput
from doc_manager_mcp.tools._internal.changes import (
    _categorize_change,
    _get_changed_files_from_checksums,
    _get_changed_files_from_git,
    _load_baseline,
    _map_to_affected_docs,
)


async def docmgr_detect_changes(params: DocmgrDetectChangesInput) -> dict[str, Any]:
    """Detect code changes without modifying baselines (pure read-only).

    This tool performs change detection but NEVER writes to symbol-baseline.json.
    Use docmgr_update_baseline to explicitly update baselines after applying doc updates.

    Args:
        params: DocmgrDetectChangesInput with project_path, mode, and options

    Returns:
        dict with detected changes, affected docs, and optional semantic changes

    Key Behavior:
        - mode="checksum": Compares file checksums against repo-baseline.json
        - mode="git_diff": Compares against git commit
        - include_semantic=True: Performs TreeSitter analysis but DOES NOT save baseline
        - Always read-only: No files are modified

    Raises:
        ValueError: If project_path doesn't exist or baseline not found
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return {
                "status": "error",
                "message": f"Project path does not exist: {project_path}"
            }

        changed_files = []
        baseline_info = {}

        # Detect changes based on mode
        if params.mode.value == "git_diff":
            if not params.since_commit:
                return {
                    "status": "error",
                    "message": "since_commit is required for git_diff mode"
                }

            changed_files = await _get_changed_files_from_git(
                project_path,
                params.since_commit
            )
            baseline_info = {
                "mode": "git_diff",
                "since_commit": params.since_commit
            }

        else:  # checksum mode
            baseline = _load_baseline(project_path)

            if not baseline:
                return {
                    "status": "error",
                    "message": (
                        "No baseline found. "
                        "Run docmgr_init to create initial baseline."
                    )
                }

            changed_files = _get_changed_files_from_checksums(project_path, baseline)
            baseline_info = {
                "mode": "checksum",
                "baseline_commit": baseline.get("git_commit"),
                "baseline_created": baseline.get("created_at")
            }

        # Categorize changes
        categorized_changes = []
        for change_info in changed_files:
            # Handle both dict and string formats for backward compatibility
            if isinstance(change_info, dict):
                file_path = change_info["file"]
                change_type = change_info.get("change_type", "modified")
            else:
                # Fallback for string format
                file_path = str(change_info)
                change_type = "modified"

            category = _categorize_change(file_path)
            categorized_changes.append({
                "file": file_path,
                "category": category,
                "change_type": change_type
            })

        # Map to affected documentation
        affected_docs = _map_to_affected_docs(categorized_changes, project_path)

        # Semantic analysis (read-only - loads baseline but DOES NOT save)
        semantic_changes = []
        if params.include_semantic:
            # Extract file paths for semantic analysis
            file_paths = [change["file"] for change in categorized_changes]
            semantic_changes = await _get_semantic_changes_readonly(
                project_path,
                file_paths
            )

        return {
            "status": "success",
            "changes_detected": len(changed_files) > 0,
            "total_changes": len(changed_files),
            "changed_files": categorized_changes,
            "affected_documentation": affected_docs,
            "semantic_changes": semantic_changes,
            "baseline_info": baseline_info,
            "note": "Read-only detection - baselines NOT updated. Use docmgr_update_baseline to refresh baselines."
        }

    except Exception as e:
        error_msg = handle_error(e, "docmgr_detect_changes")
        error_dict = {
            "status": "error",
            "message": error_msg
        }
        # enforce_response_limit returns dict unchanged when given dict (type-safe with overloads)
        return enforce_response_limit(error_dict)


async def _get_semantic_changes_readonly(
    project_path: Path,
    changed_files: list[str]
) -> list[dict[str, Any]]:
    """Perform semantic analysis without saving baseline (read-only).

    Args:
        project_path: Project root path
        changed_files: List of changed file paths

    Returns:
        list of semantic changes detected

    Note:
        This function loads the existing symbol baseline and compares with current
        symbols, but NEVER writes the new symbols back to baseline. This makes it
        truly read-only.
    """
    try:
        from ...indexing.analysis.semantic_diff import compare_symbols, load_symbol_baseline
        from ...indexing.analysis.tree_sitter import SymbolIndexer

        baseline_path = project_path / ".doc-manager" / "memory" / "symbol-baseline.json"

        if not baseline_path.exists():
            return []

        # Load existing baseline (read-only)
        old_symbols = load_symbol_baseline(baseline_path)
        if not old_symbols:
            return []

        # Index current symbols
        indexer = SymbolIndexer()
        indexer.index_project(project_path)

        # Compare symbols (use indexer.index which is dict[str, list[Symbol]])
        semantic_changes = compare_symbols(old_symbols, indexer.index)

        # *** KEY: DO NOT call save_symbol_baseline() ***
        # This keeps the function read-only

        # Convert SemanticChange objects to dicts for JSON serialization
        return [
            {
                "change_type": change.change_type,
                "symbol_name": change.name,
                "symbol_type": change.symbol_type,
                "file_path": change.file,
                "severity": change.severity,
                "old_signature": change.old_signature,
                "new_signature": change.new_signature
            }
            for change in semantic_changes
        ]

    except Exception as e:
        # Don't fail the entire detection if semantic analysis fails
        return [{
            "error": f"Semantic analysis failed: {e!s}"
        }]
