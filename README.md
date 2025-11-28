# Documentation Manager MCP Server

An MCP (Model Context Protocol) server for comprehensive documentation lifecycle management. Automates documentation creation, maintenance, quality assessment, and synchronization for software projects.

**Version:** 1.0.0

## Features

- **Automatic change detection** - Track code changes and affected documentation
- **Link validation** - Find broken links and missing assets
- **Quality assessment** - Evaluate docs against 7 quality criteria
- **Symbol tracking** - TreeSitter-based code symbol extraction
- **Dependency mapping** - Automatic code-to-docs relationships
- **Platform detection** - Auto-detect MkDocs, Sphinx, Hugo, Docusaurus, etc.
- **Documentation migration** - Restructure docs with git history preservation


## Installation

### From source (development)

```bash
git clone https://github.com/ari1110/doc-manager-mcp
cd doc-manager-mcp
pip install -e .
```

### As MCP server

Add to your MCP settings file (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "doc-manager": {
      "command": "uvx",
      "args": ["doc-manager-mcp"]
    }
  }
}
```

Or for local development:

```json
{
  "mcpServers": {
    "doc-manager": {
      "command": "uvx",
      "args": ["--from", "/path/to/doc-manager-mcp", "doc-manager-mcp"]
    }
  }
}
```

## Quick Start

### 1. Initialize for existing project

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "existing",
    "docs_path": "docs"
  }
}
```

Creates `.doc-manager.yml`, baselines, and code-to-docs mappings.

### 2. Detect changes (read-only)

```json
{
  "tool": "docmgr_detect_changes",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "checksum",
    "include_semantic": true
  }
}
```

Never writes to baselines.

### 3. Sync documentation

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "resync",
    "docs_path": "docs"
  }
}
```

Modes: `check` (read-only) or `resync` (update baselines).

## Available Tools

- **`docmgr_init`** - Initialize doc-manager for a project (modes: `existing`, `bootstrap`)
- **`docmgr_detect_changes`** - Detect code/doc changes (read-only, never writes baselines)
- **`docmgr_detect_platform`** - Auto-detect documentation platform (MkDocs, Sphinx, Hugo, etc.)
- **`docmgr_validate_docs`** - Check for broken links, missing assets, invalid code snippets
- **`docmgr_assess_quality`** - Evaluate documentation against 7 quality criteria
- **`docmgr_update_baseline`** - Update all baselines atomically (repo, symbols, dependencies)
- **`docmgr_sync`** - Orchestrate change detection + validation + quality + baseline updates
- **`docmgr_migrate`** - Restructure/migrate documentation with git history preservation

See [Tools Reference](docs/reference/tools.md) for complete API documentation.

## Architecture

### Baseline System

Doc-manager maintains 3 baseline files in `.doc-manager/memory/`:

1. `repo-baseline.json` - File checksums and metadata
2. `symbol-baseline.json` - TreeSitter code symbols (functions, classes)
3. `dependencies.json` - Code-to-docs dependency mappings

Workflow:
```
1. docmgr_init              → Create initial baselines
2. (make code changes)
3. docmgr_detect_changes    → Detect changes (read-only)
4. (update documentation)
5. docmgr_update_baseline   → Refresh baselines
```

Or use `docmgr_sync mode="resync"` to combine steps 3-5.

## Configuration

Example `.doc-manager.yml`:

```yaml
platform: mkdocs
use_gitignore: true
exclude:
  - "tests/**"
sources:
  - "src/**/*.py"
docs_path: docs
metadata:
  language: Python
  created: '2025-01-19T20:00:00'
  version: '2.0.0'
```

See [Configuration Reference](docs/reference/configuration.md) for all options.

## Development

### Running tests

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit/

# With coverage
uv run pytest --cov=doc_manager_mcp
```

### Running the server locally

```bash
# Install in development mode
pip install -e .

# Run server (stdio transport)
doc-manager-mcp

# Or with uv
uvx --from . doc-manager-mcp
```

### Linting

```bash
# Ruff (linter + formatter)
uv run ruff check .
uv run ruff format .

# Pyright (type checker)
uv run pyright
```

### Adding new tools

1. Create implementation in `doc_manager_mcp/tools/`
2. Define Pydantic model in `doc_manager_mcp/models.py`
3. Register tool in `doc_manager_mcp/server.py` with `@mcp.tool`
4. Add tests in `tests/unit/` and `tests/integration/`
5. Update documentation

## Documentation

- [Getting Started](docs/getting-started/installation.md)
- [Tools Reference](docs/reference/tools.md)
- [Configuration](docs/reference/configuration.md)
- [Troubleshooting](docs/guides/troubleshooting.md)
- [Technical Specs](specs/)

## License

MIT License
