# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is an MCP (Model Context Protocol) server for comprehensive documentation lifecycle management. It provides tools for documentation generation, migration, quality assessment, and synchronization.

## Running and Testing

### Run the MCP Server

```bash
python server.py
```

The server uses stdio transport for MCP client communication. When run directly, it will wait for stdin input (this is expected behavior).

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run python server.py
```

### Validate Python Syntax

```bash
python -m py_compile server.py
```

## Architecture

### Modular Tool Structure

The server follows a modular architecture where each tool is implemented in its own file:

- `server.py` - Main MCP server entry point using FastMCP
- `src/models.py` - Pydantic input models for all tools
- `src/constants.py` - Constants and enums
- `src/utils.py` - Shared utility functions
- `src/tools/` - Tool implementations (one file per tool/group)

### Tool Registration Pattern

All tools follow this pattern in `server.py`:

```python
@mcp.tool(
    name="docmgr_<tool_name>",
    annotations={
        "title": "Human Readable Title",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_<tool_name>(params: <ModelName>Input) -> str:
    """Tool description."""
    return await <function_name>(params)
```

### Tool Implementation Pattern

Each tool implementation in `src/tools/` follows this structure:

1. Import dependencies and models
2. Implement async function that accepts Pydantic model
3. Validate inputs (project_path exists, required files present)
4. Perform tool operation
5. Return formatted string (Markdown or JSON based on `response_format`)
6. Use `handle_error()` for exception handling

### Memory System

The memory system tracks project state in `.doc-manager/`:

- `memory/repo-baseline.json` - File checksums and repository metadata
- `memory/doc-conventions.md` - Documentation style guide (customizable)
- `asset-manifest.json` - Asset tracking

Checksums enable change detection independent of git commits, which is more reliable for documentation synchronization.

## Current Implementation Status

**Implemented Tools (3/10):**
- `docmgr_initialize_config` - Creates `.doc-manager.yml` configuration
- `docmgr_initialize_memory` - Sets up memory system with checksums
- `docmgr_detect_platform` - Detects/recommends documentation platforms

**Planned Tools:**
- Quality assessment (7 criteria: relevance, accuracy, purposefulness, uniqueness, consistency, clarity, structure)
- Documentation validation (links, assets, code snippets)
- Change mapping (detect code changes and map to affected docs)
- Dependency tracking (code-to-docs relationships)
- Bootstrap workflow (generate fresh documentation)
- Migration workflow (restructure existing docs)
- Sync workflow (incremental updates)

See NEXT-STEPS.md for detailed implementation roadmap.

## Adding New Tools

1. **Define Model** in `src/models.py`:
   ```python
   class NewToolInput(BaseModel):
       model_config = ConfigDict(
           str_strip_whitespace=True,
           validate_assignment=True,
           extra='forbid'
       )
       project_path: str = Field(..., description="...", min_length=1)
       # other fields...
   ```

2. **Create Implementation** in `src/tools/<category>.py`:
   ```python
   from ..models import NewToolInput
   from ..utils import handle_error

   async def new_tool_function(params: NewToolInput) -> str:
       try:
           # Validate inputs
           # Perform operation
           # Return formatted result
       except Exception as e:
           return handle_error(e, "new_tool_function")
   ```

3. **Register Tool** in `server.py`:
   ```python
   from src.tools.<category> import new_tool_function

   @mcp.tool(name="docmgr_new_tool", annotations={...})
   async def docmgr_new_tool(params: NewToolInput) -> str:
       """Tool description."""
       return await new_tool_function(params)
   ```

## Key Conventions

### File Paths
- All `project_path` parameters must be absolute paths
- Paths are resolved and validated using `Path.resolve()`
- Windows and Unix paths both supported

### Response Formats
- Most tools support `response_format` parameter (markdown or json)
- Default to markdown for human readability
- JSON for machine parsing/integration

### Error Handling
- Use `handle_error(exception, context)` from utils.py
- Return error messages as strings (don't raise exceptions in tools)
- Validate all inputs before processing

### Platform Detection
- Check root-level config files first (fast path)
- Fall back to detecting from project language
- Support 7 platforms: hugo, docusaurus, mkdocs, sphinx, vitepress, jekyll, gitbook

### Checksums vs Git Commits
- Use SHA-256 file checksums for change detection (more reliable)
- Git commit/branch stored for context only
- Checksums work even with uncommitted changes

## Project Configuration

### .doc-manager.yml Format

```yaml
platform: hugo
exclude:
  - '**/node_modules'
  - '**/dist'
  - '**/vendor'
  - '**/*.log'
sources: []
docs_path: docs
metadata:
  language: Go
  created: '2025-01-13T10:30:00'
  version: '1.0.0'
```

### Dependency Management
- Uses `pyproject.toml` with hatchling build backend
- Main dependencies: mcp, pydantic, pyyaml
- Python >=3.10 required

## Design Principles

1. **Modularity** - Each tool is self-contained in its own file
2. **Validation** - Use Pydantic models for all inputs
3. **Idempotency** - Tools can be run multiple times safely
4. **Error Recovery** - Return descriptive errors, don't crash
5. **Performance** - Cache expensive operations when possible
6. **Platform Agnostic** - Support multiple documentation platforms
7. **MCP Best Practices** - Follow FastMCP patterns and annotations
