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

# Import models
from src.models import (
    InitializeConfigInput,
    InitializeMemoryInput,
    DetectPlatformInput,
    ValidateDocsInput
)

# Import tool implementations
from src.tools.config import initialize_config
from src.tools.memory import initialize_memory
from src.tools.platform import detect_platform
from src.tools.validation import validate_docs

# Initialize the MCP server
mcp = FastMCP("doc_manager_mcp")

# ============================================================================
# Register Tools
# ============================================================================

@mcp.tool(
    name="docmgr_initialize_config",
    annotations={
        "title": "Initialize Documentation Manager Configuration",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_initialize_config(params: InitializeConfigInput) -> str:
    """Initialize .doc-manager.yml configuration file for the project."""
    return await initialize_config(params)

@mcp.tool(
    name="docmgr_initialize_memory",
    annotations={
        "title": "Initialize Documentation Memory System",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_initialize_memory(params: InitializeMemoryInput) -> str:
    """Initialize the documentation memory system for tracking project state."""
    return await initialize_memory(params)

@mcp.tool(
    name="docmgr_detect_platform",
    annotations={
        "title": "Detect Documentation Platform",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_detect_platform(params: DetectPlatformInput) -> str:
    """Detect and recommend documentation platform for the project."""
    return await detect_platform(params)

@mcp.tool(
    name="docmgr_validate_docs",
    annotations={
        "title": "Validate Documentation",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_validate_docs(params: ValidateDocsInput) -> str:
    """Validate documentation for broken links, missing assets, and code snippet issues."""
    return await validate_docs(params)

if __name__ == "__main__":
    mcp.run()
