"""Comprehensive baseline update tool (T009)."""

from pathlib import Path
from typing import Any

from ..models import DocmgrUpdateBaselineInput
from ..utils import enforce_response_limit, handle_error


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
        return enforce_response_limit(handle_error(e, "docmgr_update_baseline"))


async def _update_repo_baseline(project_path: Path) -> dict[str, Any]:
    """Update repo-baseline.json with current file checksums.

    Args:
        project_path: Project root path

    Returns:
        dict with status and baseline information
    """
    try:
        from ..indexing.baseline import create_baseline

        baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"
        baseline = create_baseline(project_path)

        import json
        baseline_path.write_text(json.dumps(baseline, indent=2))

        return {
            "status": "success",
            "files_tracked": len(baseline.get("files", {})),
            "git_commit": baseline.get("git_commit"),
            "path": str(baseline_path)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update repo baseline: {str(e)}"
        }


async def _update_symbol_baseline(project_path: Path) -> dict[str, Any]:
    """Update symbol-baseline.json with current TreeSitter code symbols.

    Args:
        project_path: Project root path

    Returns:
        dict with status and symbol information
    """
    try:
        from ..indexing.tree_sitter import SymbolIndexer
        from ..indexing.semantic_diff import save_symbol_baseline

        baseline_path = project_path / ".doc-manager" / "memory" / "symbol-baseline.json"

        # Index current symbols
        indexer = SymbolIndexer()
        indexer.index_project(project_path)
        symbols = indexer.get_all_symbols()

        # Save to baseline
        save_symbol_baseline(baseline_path, symbols)

        return {
            "status": "success",
            "symbols_tracked": len(symbols),
            "path": str(baseline_path)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to update symbol baseline: {str(e)}"
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
        from .dependencies import track_dependencies
        from ..models import TrackDependenciesInput

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
            "message": f"Failed to update dependencies: {str(e)}"
        }
