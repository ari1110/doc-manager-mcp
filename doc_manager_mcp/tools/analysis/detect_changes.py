"""Pure read-only change detection tool (T008).

Key difference from map_changes: NEVER writes to symbol-baseline.json
"""

from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    check_branch_mismatch,
    check_staleness,
    enforce_response_limit,
    format_staleness_warnings,
    handle_error,
    run_git_command,
)
from doc_manager_mcp.models import DocmgrDetectChangesInput
from doc_manager_mcp.tools._internal.baselines import load_repo_baseline
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

            # Load typed baseline for additional metadata
            repo_baseline_data = load_repo_baseline(project_path, validate=False)
            repo_name = repo_baseline_data.get("repo_name") if isinstance(repo_baseline_data, dict) else None
            file_count = repo_baseline_data.get("file_count", 0) if isinstance(repo_baseline_data, dict) else 0

            baseline_info = {
                "mode": "checksum",
                "repo_name": repo_name,  # Task 1.2: Include repo name in output
                "baseline_commit": baseline.get("metadata", {}).get("git_commit") if baseline.get("metadata") else baseline.get("git_commit"),
                "baseline_created": baseline.get("timestamp"),
                "baseline_branch": baseline.get("metadata", {}).get("git_branch") if baseline.get("metadata") else None,
                "file_count": file_count,  # Task 1.7: Include for change percentages
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
        config_field_changes = []
        action_items = []
        if params.include_semantic:
            # Extract file paths for semantic analysis
            file_paths = [change["file"] for change in categorized_changes]
            analysis_result = await _get_semantic_changes_readonly(
                project_path,
                file_paths,
                affected_docs,
            )
            semantic_changes = analysis_result.get("semantic_changes", [])
            config_field_changes = analysis_result.get("config_field_changes", [])
            action_items = analysis_result.get("action_items", [])

        # Check staleness and branch mismatch
        warnings = []
        if baseline_info.get("mode") == "checksum":
            # Check repo baseline staleness
            repo_staleness = check_staleness(baseline_info.get("baseline_created"))
            if repo_staleness.message:
                warnings.extend(format_staleness_warnings(repo_staleness=repo_staleness))

            # Check branch mismatch
            baseline_branch = baseline_info.get("baseline_branch")
            if baseline_branch:
                current_branch = await run_git_command(project_path, "rev-parse", "--abbrev-ref", "HEAD")
                if current_branch:
                    branch_warning = check_branch_mismatch(baseline_branch, current_branch.strip())
                    if branch_warning:
                        warnings.extend(format_staleness_warnings(branch_warning=branch_warning))

        # Task 1.7: Calculate change percentage if file_count available
        change_percentage = None
        file_count_value = baseline_info.get("file_count", 0)
        if isinstance(file_count_value, int) and file_count_value > 0:
            change_percentage = round(
                len(changed_files) / file_count_value * 100, 1
            )

        result = {
            "status": "success",
            "changes_detected": len(changed_files) > 0,
            "total_changes": len(changed_files),
            "change_percentage": change_percentage,  # Task 1.7: "X of Y files changed (Z%)"
            "changed_files": categorized_changes,
            "affected_documentation": affected_docs,
            "semantic_changes": semantic_changes,
            "config_field_changes": config_field_changes,
            "action_items": action_items,
            "baseline_info": baseline_info,
            "note": "Read-only detection - baselines NOT updated. Use docmgr_update_baseline to refresh baselines."
        }

        # Add warnings if any
        if warnings:
            result["warnings"] = warnings

        return result

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
    changed_files: list[str],
    affected_docs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Perform semantic analysis without saving baseline (read-only).

    Args:
        project_path: Project root path
        changed_files: List of changed file paths
        affected_docs: Optional list of affected documentation mappings

    Returns:
        dict with semantic_changes, config_field_changes, and action_items

    Note:
        This function loads the existing symbol baseline and compares with current
        symbols, but NEVER writes the new symbols back to baseline. This makes it
        truly read-only.
    """
    try:
        from ...core import load_config
        from ...core.actions import ActionGenerator, actions_to_dicts
        from ...indexing.analysis.semantic_diff import (
            compare_config_fields,
            compare_symbols,
            load_symbol_baseline,
        )
        from ...indexing.analysis.tree_sitter import SymbolIndexer
        from ...tools._internal.dependencies import load_dependencies

        baseline_path = project_path / ".doc-manager" / "memory" / "symbol-baseline.json"

        if not baseline_path.exists():
            return {"semantic_changes": [], "config_field_changes": [], "action_items": []}

        # Load existing baseline (read-only)
        old_symbols = load_symbol_baseline(baseline_path)
        if not old_symbols:
            return {"semantic_changes": [], "config_field_changes": [], "action_items": []}

        # Index current symbols
        indexer = SymbolIndexer()
        indexer.index_project(project_path)

        # Compare symbols (use indexer.index which is dict[str, list[Symbol]])
        semantic_changes = compare_symbols(old_symbols, indexer.index)

        # Compare config fields (T016: New feature)
        config_field_changes = compare_config_fields(old_symbols, indexer.index)

        # Load dependencies and config for ActionGenerator
        config = load_config(project_path) or {}
        docs_path = config.get("docs_path", "docs")
        doc_mappings = config.get("doc_mappings", {})

        # Try to load code_to_doc from dependencies.json
        code_to_doc: dict[str, list[str]] = {}
        try:
            deps_data = load_dependencies(project_path, validate=False)
            if deps_data:
                code_to_doc = deps_data.get("code_to_doc", {}) if isinstance(deps_data, dict) else {}
        except Exception:
            pass  # Fall back to empty code_to_doc

        # Generate action items with dependencies for precise doc inference
        action_generator = ActionGenerator(
            docs_path=docs_path,
            code_to_doc=code_to_doc,
            doc_mappings=doc_mappings,
        )
        action_items = action_generator.generate_actions(
            semantic_changes,
            config_field_changes,
            affected_docs,
        )

        # *** KEY: DO NOT call save_symbol_baseline() ***
        # This keeps the function read-only

        # Convert to dicts for JSON serialization
        return {
            "semantic_changes": [
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
            ],
            "config_field_changes": [
                {
                    "field_name": change.field_name,
                    "parent_symbol": change.parent_symbol,
                    "change_type": change.change_type,
                    "file": change.file,
                    "line": change.line,
                    "old_type": change.old_type,
                    "new_type": change.new_type,
                    "old_default": change.old_default,
                    "new_default": change.new_default,
                    "severity": change.severity,
                    "documentation_action": change.documentation_action,
                }
                for change in config_field_changes
            ],
            "action_items": actions_to_dicts(action_items),
        }

    except Exception as e:
        # Don't fail the entire detection if semantic analysis fails
        return {
            "semantic_changes": [{"error": f"Semantic analysis failed: {e!s}"}],
            "config_field_changes": [],
            "action_items": [],
        }
