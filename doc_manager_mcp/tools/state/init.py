"""Unified initialization tool for doc-manager (T007)."""

from pathlib import Path
from typing import Any

from doc_manager_mcp.core import enforce_response_limit, handle_error
from doc_manager_mcp.models import (
    BootstrapInput,
    DocmgrInitInput,
    InitializeConfigInput,
    InitializeMemoryInput,
    TrackDependenciesInput,
)
from doc_manager_mcp.tools._internal import (
    bootstrap,
    initialize_config,
    initialize_memory,
    track_dependencies,
)


async def docmgr_init(params: DocmgrInitInput, ctx=None) -> dict[str, Any]:
    """Initialize doc-manager for a project.

    Two modes:
    - mode="existing": Initialize config + baselines + dependencies for existing documentation
    - mode="bootstrap": Create fresh documentation structure + config + baselines + dependencies

    This replaces: initialize_config, initialize_memory, bootstrap

    Args:
        params: DocmgrInitInput with project_path, mode, and optional config
        ctx: Optional context for progress reporting

    Returns:
        dict with status, mode, and results from each initialization step

    Raises:
        ValueError: If project_path doesn't exist or mode is invalid
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return {
                "status": "error",
                "message": f"Project path does not exist: {project_path}"
            }

        if params.mode == "existing":
            # Step 1: Initialize configuration file
            if ctx:
                await ctx.info("Step 1/3: Initializing configuration...")

            config_result = await initialize_config(InitializeConfigInput(
                project_path=str(project_path),
                platform=params.platform,
                exclude_patterns=params.exclude_patterns,
                docs_path=params.docs_path,
                sources=params.sources
            ))

            # Step 2: Initialize memory system (baselines)
            if ctx:
                await ctx.info("Step 2/3: Initializing memory system...")

            memory_result = await initialize_memory(
                InitializeMemoryInput(project_path=str(project_path)),
                ctx
            )

            # Check for memory initialization failure
            if isinstance(memory_result, dict) and memory_result.get("status") == "error":
                return memory_result  # Propagate error

            # Step 3: Track dependencies
            if ctx:
                await ctx.info("Step 3/3: Tracking dependencies...")

            deps_result = await track_dependencies(TrackDependenciesInput(
                project_path=str(project_path),
                docs_path=params.docs_path
            ))

            # Check for dependency tracking failure
            if isinstance(deps_result, dict) and deps_result.get("status") == "error":
                return deps_result  # Propagate error

            return {
                "status": "success",
                "message": "Initialized doc-manager for existing project",
                "mode": "existing",
                "steps_completed": {
                    "config": "created" if isinstance(config_result, dict) and config_result.get("status") == "success" else "completed",
                    "memory": "created" if isinstance(memory_result, dict) and memory_result.get("status") == "success" else "completed",
                    "dependencies": "created" if isinstance(deps_result, dict) and deps_result.get("status") == "success" else "completed"
                },
                "config_path": f"{project_path}/.doc-manager.yml",
                "memory_path": f"{project_path}/.doc-manager/memory/",
                "dependencies_path": f"{project_path}/.doc-manager/dependencies.json"
            }

        elif params.mode == "bootstrap":
            # Use existing bootstrap workflow which creates:
            # - docs/ directory with templates
            # - .doc-manager.yml config
            # - .doc-manager/memory/ baselines
            if ctx:
                await ctx.info("Bootstrapping fresh documentation...")

            bootstrap_result = await bootstrap(BootstrapInput(
                project_path=str(project_path),
                platform=params.platform,
                docs_path=params.docs_path or "docs"
            ))

            # Add dependency tracking (not included in bootstrap)
            if ctx:
                await ctx.info("Tracking dependencies...")

            deps_result = await track_dependencies(TrackDependenciesInput(
                project_path=str(project_path),
                docs_path=params.docs_path or "docs"
            ))

            # Check for dependency tracking failure
            if isinstance(deps_result, dict) and deps_result.get("status") == "error":
                return deps_result  # Propagate error

            return {
                "status": "success",
                "message": "Bootstrapped fresh documentation structure",
                "mode": "bootstrap",
                "bootstrap_result": bootstrap_result if isinstance(bootstrap_result, dict) else {"completed": True},
                "dependencies_tracked": isinstance(deps_result, dict) and deps_result.get("status") == "success",
                "docs_path": params.docs_path or "docs"
            }

        else:
            return {
                "status": "error",
                "message": f"Invalid mode: {params.mode}. Must be 'existing' or 'bootstrap'"
            }

    except Exception as e:
        error_msg = handle_error(e, "docmgr_init")
        error_dict = {
            "status": "error",
            "message": error_msg
        }
        # enforce_response_limit returns dict unchanged when given dict (type-safe with overloads)
        return enforce_response_limit(error_dict)
