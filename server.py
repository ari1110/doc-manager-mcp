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

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

# Import constants for enum conversions
from src.constants import (
    ChangeDetectionMode,
    DocumentationPlatform,
    QualityCriterion,
)

# Import models
from src.models import (
    AssessQualityInput,
    BootstrapInput,
    DetectPlatformInput,
    InitializeConfigInput,
    InitializeMemoryInput,
    MapChangesInput,
    MigrateInput,
    SyncInput,
    TrackDependenciesInput,
    ValidateDocsInput,
)
from src.tools.changes import map_changes

# Import tool implementations
from src.tools.config import initialize_config
from src.tools.dependencies import track_dependencies
from src.tools.memory import initialize_memory
from src.tools.platform import detect_platform
from src.tools.quality import assess_quality
from src.tools.validation import validate_docs
from src.tools.workflows import bootstrap, migrate, sync

# Initialize the MCP server
mcp = FastMCP("doc_manager_mcp")

# ============================================================================
# Register Tools
# ============================================================================

@mcp.tool(
    name="docmgr_initialize_config",
    annotations=ToolAnnotations(
        title="Initialize Documentation Manager Configuration",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_initialize_config(
    project_path: str,
    platform: str | None = None,
    exclude_patterns: list[str] | None = None,
    docs_path: str | None = None,
    sources: list[str] | None = None
) -> str | dict[str, Any]:
    """Initialize .doc-manager.yml configuration file for the project."""
    # Pass user patterns only (max 50 items constraint)
    # Tools will merge with DEFAULT_EXCLUDE_PATTERNS when loading config
    params = InitializeConfigInput(
        project_path=project_path,
        platform=DocumentationPlatform(platform) if platform else None,
        exclude_patterns=exclude_patterns,
        docs_path=docs_path,
        sources=sources
    )
    return await initialize_config(params)

@mcp.tool(
    name="docmgr_initialize_memory",
    annotations=ToolAnnotations(
        title="Initialize Documentation Memory System",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_initialize_memory(
    project_path: str,
    ctx: mcp.Context
) -> str | dict[str, Any]:
    """Initialize the documentation memory system for tracking project state."""
    params = InitializeMemoryInput(
        project_path=project_path
    )
    return await initialize_memory(params, ctx)

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
    check_snippets: bool = True
) -> str | dict[str, Any]:
    """Validate documentation for broken links, missing assets, and code snippet issues."""
    params = ValidateDocsInput(
        project_path=project_path,
        docs_path=docs_path,
        check_links=check_links,
        check_assets=check_assets,
        check_snippets=check_snippets
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

@mcp.tool(
    name="docmgr_map_changes",
    annotations=ToolAnnotations(
        title="Map Code Changes to Documentation",
        readOnlyHint=False,  # T047: Writes to memory baseline
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_map_changes(
    project_path: str,
    since_commit: str | None = None,
    mode: str = "checksum"
) -> str | dict[str, Any]:
    """Map code changes to affected documentation using checksum comparison or git diff."""
    params = MapChangesInput(
        project_path=project_path,
        since_commit=since_commit,
        mode=ChangeDetectionMode(mode)
    )
    return await map_changes(params)

@mcp.tool(
    name="docmgr_track_dependencies",
    annotations=ToolAnnotations(
        title="Track Code-to-Documentation Dependencies",
        readOnlyHint=False,  # T048: Writes dependencies.json file
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_track_dependencies(
    project_path: str,
    docs_path: str | None = None
) -> str | dict[str, Any]:
    """Build dependency graph showing which docs reference which source files."""
    params = TrackDependenciesInput(
        project_path=project_path,
        docs_path=docs_path
    )
    return await track_dependencies(params)

@mcp.tool(
    name="docmgr_bootstrap",
    annotations=ToolAnnotations(
        title="Bootstrap Fresh Documentation",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False
    )
)
async def docmgr_bootstrap(
    project_path: str,
    platform: str | None = None,
    docs_path: str = "docs"
) -> str | dict[str, Any]:
    """Bootstrap fresh documentation structure with templates and configuration."""
    params = BootstrapInput(
        project_path=project_path,
        platform=DocumentationPlatform(platform) if platform else None,
        docs_path=docs_path
    )
    return await bootstrap(params)

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
    preserve_history: bool = True
) -> str | dict[str, Any]:
    """Migrate existing documentation to new structure with optional git history preservation."""
    params = MigrateInput(
        project_path=project_path,
        source_path=source_path,
        target_path=target_path,
        target_platform=DocumentationPlatform(target_platform) if target_platform else None,
        preserve_history=preserve_history
    )
    return await migrate(params)

@mcp.tool(
    name="docmgr_sync",
    annotations=ToolAnnotations(
        title="Sync Documentation with Code Changes",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_sync(
    project_path: str,
    mode: str = "reactive",
    docs_path: str | None = None
) -> str | dict[str, Any]:
    """Sync documentation with code changes, identifying what needs updates."""
    params = SyncInput(
        project_path=project_path,
        mode=mode,
        docs_path=docs_path
    )
    return await sync(params)

if __name__ == "__main__":
    mcp.run()
