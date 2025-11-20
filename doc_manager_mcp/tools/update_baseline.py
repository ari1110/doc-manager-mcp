"""Comprehensive baseline update tool (T009)."""

from pathlib import Path
from typing import Any, cast

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
        error_msg = handle_error(e, "docmgr_update_baseline")
        error_dict = {
            "status": "error",
            "message": error_msg
        }
        # enforce_response_limit returns dict unchanged when given dict
        return cast(dict[str, Any], enforce_response_limit(error_dict))


async def _update_repo_baseline(project_path: Path) -> dict[str, Any]:
    """Update repo-baseline.json with current file checksums.

    Args:
        project_path: Project root path

    Returns:
        dict with status and baseline information
    """
    try:
        import json
        from datetime import datetime

        from ..constants import DEFAULT_EXCLUDE_PATTERNS, MAX_FILES
        from ..utils import (
            calculate_checksum,
            detect_project_language,
            find_docs_directory,
            load_config,
            matches_exclude_pattern,
            run_git_command,
        )

        # Load config and build exclude patterns
        config = load_config(project_path)
        user_excludes = config.get("exclude", []) if config else []
        exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS) + user_excludes

        # Scan files and calculate checksums
        checksums = {}
        file_count = 0

        for root, _dirs, files in project_path.walk():
            if file_count >= MAX_FILES:
                break

            for file in files:
                if file_count >= MAX_FILES:
                    break

                file_path = root / file
                relative_path = str(file_path.relative_to(project_path)).replace('\\', '/')

                if matches_exclude_pattern(relative_path, exclude_patterns):
                    continue

                checksums[relative_path] = calculate_checksum(file_path)
                file_count += 1

        # Get git info
        git_commit = await run_git_command(project_path, "rev-parse", "HEAD")
        git_branch = await run_git_command(project_path, "rev-parse", "--abbrev-ref", "HEAD")

        # Detect project metadata
        language = detect_project_language(project_path)
        docs_dir = find_docs_directory(project_path)

        # Create baseline
        baseline = {
            "repo_name": project_path.name,
            "description": f"Repository for {project_path.name}",
            "language": language,
            "docs_exist": docs_dir is not None,
            "docs_path": str(docs_dir.relative_to(project_path)) if docs_dir else None,
            "metadata": {
                "git_commit": git_commit,
                "git_branch": git_branch
            },
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "file_count": file_count,
            "files": checksums
        }

        # Write baseline
        baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"
        baseline_path.write_text(json.dumps(baseline, indent=2))

        return {
            "status": "success",
            "files_tracked": file_count,
            "git_commit": git_commit,
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
        from ..indexing.semantic_diff import save_symbol_baseline
        from ..indexing.tree_sitter import SymbolIndexer

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
        from ..models import TrackDependenciesInput
        from .dependencies import track_dependencies

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
