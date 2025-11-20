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
    DetectPlatformInput,
    DocmgrDetectChangesInput,
    DocmgrInitInput,
    DocmgrUpdateBaselineInput,
    MigrateInput,
    SyncInput,
    TrackDependenciesInput,
    ValidateDocsInput,
)

# Import tool implementations
from .tools.dependencies import track_dependencies
from .tools.detect_changes import docmgr_detect_changes
from .tools.init import docmgr_init
from .tools.platform import detect_platform
from .tools.quality import assess_quality
from .tools.update_baseline import docmgr_update_baseline
from .tools.validation import validate_docs
from .tools.workflows import migrate, sync

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
