"""Comprehensive baseline update tool (T009)."""

from pathlib import Path
from typing import Any

from doc_manager_mcp.core import enforce_response_limit, handle_error
from doc_manager_mcp.core.security import file_lock
from doc_manager_mcp.models import DocmgrUpdateBaselineInput


async def docmgr_update_baseline(
    params: DocmgrUpdateBaselineInput,
    ctx=None
) -> dict[str, Any]:
    """Update all baseline files atomically.

    Updates three baseline files:
    - repo-baseline.json (file checksums)
    - symbol-baseline.json (TreeSitter code symbols)
    - dependencies.json (code-to-doc mappings)

    This tool should be called after applying documentation updates to ensure
    baselines reflect the current state of the codebase.

    Args:
        params: DocmgrUpdateBaselineInput with project_path and optional docs_path
        ctx: Optional context for progress reporting

    Returns:
        dict with status and updated baseline information

    Raises:
        ValueError: If project_path doesn't exist or .doc-manager not initialized
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return {
                "status": "error",
                "message": f"Project path does not exist: {project_path}"
            }

        memory_path = project_path / ".doc-manager" / "memory"
        if not memory_path.exists():
            return {
                "status": "error",
                "message": (
                    "Memory system not initialized. "
                    "Run docmgr_init first."
                )
            }

        updated_files = []

        # Step 1: Update repo baseline (file checksums)
        if ctx:
            await ctx.info("Updating repo baseline (file checksums)...")

        repo_result = await _update_repo_baseline(project_path)
        if repo_result.get("status") == "success":
            updated_files.append("repo-baseline.json")

        # Step 2: Update symbol baseline (TreeSitter code symbols)
        if ctx:
            await ctx.info("Updating symbol baseline (code symbols)...")

        symbol_result = await _update_symbol_baseline(project_path)
        if symbol_result.get("status") == "success":
            updated_files.append("symbol-baseline.json")

        # Step 3: Update dependencies (code-to-doc mappings)
        if ctx:
            await ctx.info("Updating dependencies (code-to-doc mappings)...")

        deps_path = params.docs_path or "docs"
        deps_result = await _update_dependencies(project_path, deps_path)
        if deps_result.get("status") == "success":
            updated_files.append("dependencies.json")

        return {
            "status": "success",
            "message": "All baselines updated successfully",
            "updated_files": updated_files,
            "details": {
                "repo_baseline": repo_result,
                "symbol_baseline": symbol_result,
                "dependencies": deps_result
            }
        }

    except Exception as e:
        error_msg = handle_error(e, "docmgr_update_baseline")
        error_dict = {
            "status": "error",
            "message": error_msg
        }
        # enforce_response_limit returns dict unchanged when given dict (type-safe with overloads)
        return enforce_response_limit(error_dict)


def _calculate_file_checksums(project_path: Path) -> tuple[dict[str, str], int]:
    """Calculate checksums for all project files.

    Args:
        project_path: Project root path

    Returns:
        Tuple of (checksums dict, file count)
    """
    from doc_manager_mcp.constants import MAX_FILES
    from doc_manager_mcp.core import calculate_checksum
    from doc_manager_mcp.core.file_scanner import scan_project_files

    checksums = {}
    file_count = 0

    for file_path in scan_project_files(project_path, max_files=MAX_FILES, use_walk=True):
        relative_path = str(file_path.relative_to(project_path)).replace('\\', '/')
        checksums[relative_path] = calculate_checksum(file_path)
        file_count += 1

    return checksums, file_count


async def _get_git_metadata(project_path: Path) -> dict[str, str | None]:
    """Get git commit and branch information.

    Args:
        project_path: Project root path

    Returns:
        Dict with git_commit and git_branch
    """
    from doc_manager_mcp.core import run_git_command

    git_commit = await run_git_command(project_path, "rev-parse", "HEAD")
    git_branch = await run_git_command(project_path, "rev-parse", "--abbrev-ref", "HEAD")

    return {
        "git_commit": git_commit,
        "git_branch": git_branch
    }


def _build_baseline_structure(
    project_path: Path,
    checksums: dict[str, str],
    file_count: int,
    git_metadata: dict[str, str | None]
) -> dict[str, Any]:
    """Build baseline structure with all metadata.

    Args:
        project_path: Project root path
        checksums: File checksums dict
        file_count: Number of files tracked
        git_metadata: Git commit and branch info

    Returns:
        Complete baseline structure
    """
    from datetime import datetime

    from doc_manager_mcp.core import detect_project_language, find_docs_directory

    language = detect_project_language(project_path)
    docs_dir = find_docs_directory(project_path)

    return {
        "repo_name": project_path.name,
        "description": f"Repository for {project_path.name}",
        "language": language,
        "docs_exist": docs_dir is not None,
        "docs_path": str(docs_dir.relative_to(project_path)) if docs_dir else None,
        "metadata": git_metadata,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "file_count": file_count,
        "files": checksums
    }


def _write_baseline_safely(baseline_path: Path, baseline: dict[str, Any]) -> None:
    """Write baseline to disk with file locking.

    Args:
        baseline_path: Path to baseline file
        baseline: Baseline data structure
    """
    import json

    with file_lock(baseline_path, timeout=10, retries=3):
        baseline_path.write_text(json.dumps(baseline, indent=2))


async def _update_repo_baseline(project_path: Path) -> dict[str, Any]:
    """Update repo-baseline.json with current file checksums.

    Args:
        project_path: Project root path

    Returns:
        dict with status and baseline information
    """
    try:
        # Calculate file checksums
        checksums, file_count = _calculate_file_checksums(project_path)

        # Get git metadata
        git_metadata = await _get_git_metadata(project_path)

        # Build baseline structure
        baseline = _build_baseline_structure(
            project_path,
            checksums,
            file_count,
            git_metadata
        )

        # Write baseline safely
        baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"
        _write_baseline_safely(baseline_path, baseline)

        return {
            "status": "success",
            "files_tracked": file_count,
            "git_commit": git_metadata["git_commit"],
            "path": str(baseline_path)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update repo baseline: {e!s}"
        }


async def _update_symbol_baseline(project_path: Path) -> dict[str, Any]:
    """Update symbol-baseline.json with current TreeSitter code symbols.

    Args:
        project_path: Project root path

    Returns:
        dict with status and symbol information
    """
    try:
        from ...indexing.analysis.semantic_diff import save_symbol_baseline
        from ...indexing.analysis.tree_sitter import SymbolIndexer

        baseline_path = project_path / ".doc-manager" / "memory" / "symbol-baseline.json"

        # Index current symbols
        indexer = SymbolIndexer()
        indexer.index_project(project_path)

        # Save to baseline (use indexer.index which is dict[str, list[Symbol]])
        save_symbol_baseline(baseline_path, indexer.index)

        # Count total symbols
        total_symbols = sum(len(symbols) for symbols in indexer.index.values())

        return {
            "status": "success",
            "symbols_tracked": total_symbols,
            "path": str(baseline_path)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update symbol baseline: {e!s}"
        }


async def _update_dependencies(
    project_path: Path,
    docs_path: str
) -> dict[str, Any]:
    """Update dependencies.json with current code-to-doc mappings.

    Args:
        project_path: Project root path
        docs_path: Documentation directory path

    Returns:
        dict with status and dependency information
    """
    try:
        from doc_manager_mcp.models import TrackDependenciesInput
        from doc_manager_mcp.tools._internal import track_dependencies

        # Reuse existing track_dependencies function
        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(project_path),
            docs_path=docs_path
        ))

        return {
            "status": "success",
            "dependencies_tracked": result.get("total_dependencies", 0),
            "path": str(project_path / ".doc-manager" / "dependencies.json")
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update dependencies: {e!s}"
        }
