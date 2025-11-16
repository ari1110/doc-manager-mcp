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
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

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
async def docmgr_initialize_config(params: InitializeConfigInput) -> str:
    """Initialize .doc-manager.yml configuration file for the project."""
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
async def docmgr_initialize_memory(params: InitializeMemoryInput) -> str:
    """Initialize the documentation memory system for tracking project state."""
    return await initialize_memory(params)

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
async def docmgr_detect_platform(params: DetectPlatformInput) -> str:
    """Detect and recommend documentation platform for the project."""
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
async def docmgr_validate_docs(params: ValidateDocsInput) -> str:
    """Validate documentation for broken links, missing assets, and code snippet issues."""
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
async def docmgr_assess_quality(params: AssessQualityInput) -> str:
    """Assess documentation quality against 7 criteria: relevance, accuracy, purposefulness,
    uniqueness, consistency, clarity, structure.
    """
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
async def docmgr_map_changes(params: MapChangesInput) -> str:
    """Map code changes to affected documentation using checksum comparison or git diff."""
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
async def docmgr_track_dependencies(params: TrackDependenciesInput) -> str:
    """Build dependency graph showing which docs reference which source files."""
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
async def docmgr_bootstrap(params: BootstrapInput) -> str:
    """Bootstrap fresh documentation structure with templates and configuration."""
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
async def docmgr_migrate(params: MigrateInput) -> str:
    """Migrate existing documentation to new structure with optional git history preservation."""
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
async def docmgr_sync(params: SyncInput) -> str:
    """Sync documentation with code changes, identifying what needs updates."""
    return await sync(params)

if __name__ == "__main__":
    mcp.run()
