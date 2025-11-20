#!/usr/bin/env python3
"""
Documentation Manager MCP Server

An MCP server for comprehensive documentation lifecycle management including:
- Documentation generation (bootstrap)
- Migration and restructuring
- Incremental synchronization
- Quality assessment (7 criteria)
- Validation (links, assets, code snippets)
- Monorepo support
- Testing change detection
"""

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

# Import constants for enum conversions
from .constants import (
    ChangeDetectionMode,
    DocumentationPlatform,
    QualityCriterion,
)

# Import models
from .models import (
    AssessQualityInput,
    BootstrapInput,
    DetectPlatformInput,
    DocmgrDetectChangesInput,
    DocmgrInitInput,
    DocmgrUpdateBaselineInput,
    InitializeConfigInput,
    InitializeMemoryInput,
    MapChangesInput,
    MigrateInput,
    SyncInput,
    TrackDependenciesInput,
    ValidateDocsInput,
)
from .tools.changes import map_changes

# Import tool implementations
from .tools.config import initialize_config
from .tools.dependencies import track_dependencies
from .tools.detect_changes import docmgr_detect_changes
from .tools.init import docmgr_init
from .tools.memory import initialize_memory
from .tools.platform import detect_platform
from .tools.quality import assess_quality
from .tools.update_baseline import docmgr_update_baseline
from .tools.validation import validate_docs
from .tools.workflows import bootstrap, migrate, sync

# Fix Windows asyncio event loop for subprocess support
# Windows requires ProactorEventLoop for asyncio.create_subprocess_exec
# Uvicorn defaults to SelectorEventLoop which doesn't support subprocess
import asyncio
import platform

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Initialize the MCP server
mcp = FastMCP("doc_manager_mcp")

# ============================================================================
# Register Tools
# ============================================================================

# ----------------------------------------------------------------------------
# Tier 1: Setup & Initialization
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_init",
    annotations=ToolAnnotations(
        title="Initialize Documentation Manager",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def tool_docmgr_init(
    project_path: str,
    mode: str = "existing",
    platform: str | None = None,
    exclude_patterns: list[str] | None = None,
    docs_path: str | None = None,
    sources: list[str] | None = None,
    ctx: Context | None = None
) -> dict[str, Any]:
    """Initialize doc-manager for a project.

    Unified initialization tool that replaces: initialize_config, initialize_memory, bootstrap.

    Modes:
    - mode="existing": Initialize config + baselines + dependencies for existing project
    - mode="bootstrap": Create fresh docs + config + baselines + dependencies

    This is the recommended entry point for setting up doc-manager.
    """
    params = DocmgrInitInput(
        project_path=project_path,
        mode=mode,
        platform=DocumentationPlatform(platform) if platform else None,
        exclude_patterns=exclude_patterns,
        docs_path=docs_path,
        sources=sources
    )
    return await docmgr_init(params, ctx)

# ----------------------------------------------------------------------------
# Tier 2: Analysis & Read-Only Operations
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_detect_changes",
    annotations=ToolAnnotations(
        title="Detect Code Changes (Read-Only)",
        readOnlyHint=True,  # NEVER writes to baselines
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def tool_docmgr_detect_changes(
    project_path: str,
    since_commit: str | None = None,
    mode: str = "checksum",
    include_semantic: bool = False
) -> dict[str, Any]:
    """Detect code changes without modifying baselines (pure read-only).

    Key difference from map_changes: NEVER writes to symbol-baseline.json.

    Modes:
    - mode="checksum": Compare file checksums against repo-baseline.json
    - mode="git_diff": Compare against git commit

    Use docmgr_update_baseline to explicitly update baselines after applying doc updates.
    """
    params = DocmgrDetectChangesInput(
        project_path=project_path,
        since_commit=since_commit,
        mode=ChangeDetectionMode(mode),
        include_semantic=include_semantic
    )
    return await docmgr_detect_changes(params)

# ----------------------------------------------------------------------------
# Tier 3: State Management
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_update_baseline",
    annotations=ToolAnnotations(
        title="Update All Baselines",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def tool_docmgr_update_baseline(
    project_path: str,
    docs_path: str | None = None,
    ctx: Context | None = None
) -> dict[str, Any]:
    """Update all baseline files atomically.

    Updates three baselines:
    - repo-baseline.json (file checksums)
    - symbol-baseline.json (TreeSitter code symbols)
    - dependencies.json (code-to-doc mappings)

    Call this after applying documentation updates to ensure baselines reflect current state.
    """
    params = DocmgrUpdateBaselineInput(
        project_path=project_path,
        docs_path=docs_path
    )
    return await docmgr_update_baseline(params, ctx)

# ----------------------------------------------------------------------------
# Legacy Tools (Deprecated - Use docmgr_init instead)
# ----------------------------------------------------------------------------
# Commented out to provide clean 7-tool interface during testing
# Uncomment for backward compatibility if needed

# @mcp.tool(
#     name="docmgr_initialize_config",
#     annotations=ToolAnnotations(
#         title="Initialize Documentation Manager Configuration",
#         readOnlyHint=False,
#         destructiveHint=False,
#         idempotentHint=True,
#         openWorldHint=False
#     )
# )
# async def docmgr_initialize_config(
#     project_path: str,
#     platform: str | None = None,
#     exclude_patterns: list[str] | None = None,
#     docs_path: str | None = None,
#     sources: list[str] | None = None
# ) -> str | dict[str, Any]:
#     """DEPRECATED: Use docmgr_init with mode="existing" instead.
#
#     Initialize .doc-manager.yml configuration file for the project.
#
#     This tool is maintained for backward compatibility but will be removed in v2.0.
#     """
#     # Pass user patterns only (max 50 items constraint)
#     # Tools will merge with DEFAULT_EXCLUDE_PATTERNS when loading config
#     params = InitializeConfigInput(
#         project_path=project_path,
#         platform=DocumentationPlatform(platform) if platform else None,
#         exclude_patterns=exclude_patterns,
#         docs_path=docs_path,
#         sources=sources
#     )
#     return await initialize_config(params)

# @mcp.tool(
#     name="docmgr_initialize_memory",
#     annotations=ToolAnnotations(
#         title="Initialize Documentation Memory System",
#         readOnlyHint=False,
#         destructiveHint=False,
#         idempotentHint=True,
#         openWorldHint=False
#     )
# )
# async def docmgr_initialize_memory(
#     project_path: str,
#     ctx: Context
# ) -> str | dict[str, Any]:
#     """DEPRECATED: Use docmgr_init with mode="existing" instead.
#
#     Initialize the documentation memory system for tracking project state.
#
#     This tool is maintained for backward compatibility but will be removed in v2.0.
#     """
#     params = InitializeMemoryInput(
#         project_path=project_path
#     )
#     return await initialize_memory(params, ctx)

# ----------------------------------------------------------------------------
# Tier 2: Analysis & Read-Only Operations (continued)
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_detect_platform",
    annotations=ToolAnnotations(
        title="Detect Documentation Platform",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_detect_platform(
    project_path: str
) -> str | dict[str, Any]:
    """Detect and recommend documentation platform for the project."""
    params = DetectPlatformInput(
        project_path=project_path
    )
    return await detect_platform(params)

@mcp.tool(
    name="docmgr_validate_docs",
    annotations=ToolAnnotations(
        title="Validate Documentation",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_validate_docs(
    project_path: str,
    docs_path: str | None = None,
    check_links: bool = True,
    check_assets: bool = True,
    check_snippets: bool = True,
    validate_code_syntax: bool = False,
    validate_symbols: bool = False
) -> str | dict[str, Any]:
    """Validate documentation for broken links, missing assets, and code snippet issues."""
    params = ValidateDocsInput(
        project_path=project_path,
        docs_path=docs_path,
        check_links=check_links,
        check_assets=check_assets,
        check_snippets=check_snippets,
        validate_code_syntax=validate_code_syntax,
        validate_symbols=validate_symbols
    )
    return await validate_docs(params)

@mcp.tool(
    name="docmgr_assess_quality",
    annotations=ToolAnnotations(
        title="Assess Documentation Quality",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_assess_quality(
    project_path: str,
    docs_path: str | None = None,
    criteria: list[str] | None = None
) -> str | dict[str, Any]:
    """Assess documentation quality against 7 criteria: relevance, accuracy, purposefulness,
    uniqueness, consistency, clarity, structure.
    """
    params = AssessQualityInput(
        project_path=project_path,
        docs_path=docs_path,
        criteria=[QualityCriterion(c) for c in criteria] if criteria else None
    )
    return await assess_quality(params)

# @mcp.tool(
#     name="docmgr_map_changes",
#     annotations=ToolAnnotations(
#         title="Map Code Changes to Documentation",
#         readOnlyHint=False,  # T047: Writes to memory baseline
#         destructiveHint=False,
#         idempotentHint=True,
#         openWorldHint=False
#     )
# )
# async def docmgr_map_changes(
#     project_path: str,
#     since_commit: str | None = None,
#     mode: str = "checksum",
#     include_semantic: bool = False
# ) -> str | dict[str, Any]:
#     """DEPRECATED: Use docmgr_detect_changes (read-only) or docmgr_sync (orchestration) instead.
#
#     Map code changes to affected documentation using checksum comparison or git diff.
#
#     This tool is maintained for backward compatibility but will be removed in v2.0.
#     Note: This tool writes to symbol-baseline.json. Use docmgr_detect_changes for read-only detection.
#     """
#     params = MapChangesInput(
#         project_path=project_path,
#         since_commit=since_commit,
#         mode=ChangeDetectionMode(mode),
#         include_semantic=include_semantic
#     )
#     return await map_changes(params)

# ----------------------------------------------------------------------------
# Tier 3: State Management (continued)
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_track_dependencies",
    annotations=ToolAnnotations(
        title="Track Code-to-Documentation Dependencies",
        readOnlyHint=False,  # Writes dependencies.json file
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_track_dependencies(
    project_path: str,
    docs_path: str | None = None
) -> str | dict[str, Any]:
    """Build dependency graph showing which docs reference which source files.

    Note: This is also called automatically by docmgr_init and docmgr_update_baseline.
    Use this tool when you need to explicitly rebuild the dependency graph.
    """
    params = TrackDependenciesInput(
        project_path=project_path,
        docs_path=docs_path
    )
    return await track_dependencies(params)

# ----------------------------------------------------------------------------
# Legacy Tools (Deprecated)
# ----------------------------------------------------------------------------

# @mcp.tool(
#     name="docmgr_bootstrap",
#     annotations=ToolAnnotations(
#         title="Bootstrap Fresh Documentation",
#         readOnlyHint=False,
#         destructiveHint=False,
#         idempotentHint=False,
#         openWorldHint=False
#     )
# )
# async def docmgr_bootstrap(
#     project_path: str,
#     platform: str | None = None,
#     docs_path: str = "docs"
# ) -> str | dict[str, Any]:
#     """DEPRECATED: Use docmgr_init with mode="bootstrap" instead.
#
#     Bootstrap fresh documentation structure with templates and configuration.
#
#     This tool is maintained for backward compatibility but will be removed in v2.0.
#     """
#     params = BootstrapInput(
#         project_path=project_path,
#         platform=DocumentationPlatform(platform) if platform else None,
#         docs_path=docs_path
#     )
#     return await bootstrap(params)

# ----------------------------------------------------------------------------
# Tier 4: Workflows & Orchestration
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_migrate",
    annotations=ToolAnnotations(
        title="Migrate Documentation Structure",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False
    )
)
async def docmgr_migrate(
    project_path: str,
    source_path: str,
    target_path: str = "docs",
    target_platform: str | None = None,
    preserve_history: bool = True,
    rewrite_links: bool = False,
    regenerate_toc: bool = False,
    dry_run: bool = False
) -> str | dict[str, Any]:
    """Migrate existing documentation to new structure with optional git history preservation."""
    params = MigrateInput(
        project_path=project_path,
        source_path=source_path,
        target_path=target_path,
        target_platform=DocumentationPlatform(target_platform) if target_platform else None,
        preserve_history=preserve_history,
        rewrite_links=rewrite_links,
        regenerate_toc=regenerate_toc,
        dry_run=dry_run
    )
    return await migrate(params)

@mcp.tool(
    name="docmgr_sync",
    annotations=ToolAnnotations(
        title="Sync Documentation with Code Changes",
        readOnlyHint=False,  # mode="resync" updates baselines
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_sync(
    project_path: str,
    mode: str = "check",
    docs_path: str | None = None
) -> str | dict[str, Any]:
    """Sync documentation with code changes, identifying what needs updates.

    Modes:
    - mode="check": Read-only analysis (detects changes, no baseline updates)
    - mode="resync": Full sync (detects changes + updates baselines atomically)

    Orchestrates validation, quality assessment, and optional baseline updates.
    """
    params = SyncInput(
        project_path=project_path,
        mode=mode,
        docs_path=docs_path
    )
    return await sync(params)

def main():
    """Entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
