# Documentation Manager MCP Server

[![PyPI version](https://img.shields.io/pypi/v/doc-manager-mcp.svg)](https://pypi.org/project/doc-manager-mcp/)
[![Python Version](https://img.shields.io/pypi/pyversions/doc-manager-mcp)](https://pypi.org/project/doc-manager-mcp/)
[![License](https://img.shields.io/github/license/ari1110/doc-manager-mcp)](https://github.com/ari1110/doc-manager-mcp/blob/main/LICENSE)

An MCP (Model Context Protocol) server for comprehensive documentation lifecycle management. Automates documentation creation, maintenance, quality assessment, and synchronization for software projects.

## Features

- **Automatic change detection** - Track code changes and affected documentation
- **Link validation** - Find broken links and missing assets
- **Quality assessment** - Evaluate docs against 7 quality criteria
- **Symbol tracking** - TreeSitter-based code symbol extraction
- **Dependency mapping** - Automatic code-to-docs relationships
- **Platform detection** - Auto-detect MkDocs, Sphinx, Hugo, Docusaurus, etc.
- **Documentation migration** - Restructure docs with git history preservation


## Installation

### Claude Code (Recommended)

Add to your **project-level** `.mcp.json` in your project root:

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

> **⚠️ Important**: Only add this MCP server at the **project level**. Do not add it to user-level or global MCP configuration. The doc-manager tracks project-specific baselines and documentation state that should not be shared across projects.

### Claude Desktop

Add to your `claude_desktop_config.json`:

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

The MCP client will automatically download and run the server when needed.

See [Installation Guide](docs/getting-started/installation.md) for local development setup and alternative installation methods.

## Claude Code Plugin

For Claude Code users, a plugin is available that provides a streamlined documentation workflow with specialized agents and commands.

### Installation

```bash
# Install the plugin from the repository
claude plugin install /path/to/doc-manager-mcp/claude-plugin
```

Or if published to a marketplace:
```bash
claude plugin install doc-manager@marketplace-name
```

### What's Included

**Agents**:
- `@doc-expert` - Documentation lifecycle orchestrator (setup, analysis, quality assessment)
- `@doc-writer` - Content writer and updater (creates/edits documentation)

**Slash Commands**:
- `/doc-status` - Quick health check
- `/doc-sync` - Full sync workflow (detect → update → validate → assess)
- `/doc-quality` - Quality assessment with actionable findings

**Skill**:
- `doc-management` - Gentle reminders about documentation status

### Quick Usage

```bash
# Setup documentation management
@doc-expert Set up documentation management for this project

# Check status
/doc-status

# Sync after code changes
/doc-sync

# Assess quality before release
/doc-quality

# Update specific documentation
@doc-writer Update the API documentation for the new authentication endpoints
```

The plugin provides a feedback loop where @doc-expert analyzes changes, @doc-writer creates content, and @doc-expert validates quality before updating baselines.

## Quick Start

Initialize for your project:

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "existing"
  }
}
```

Then sync documentation changes:

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "check"
  }
}
```

See [Quick Start Guide](docs/getting-started/quick-start.md) for step-by-step instructions and workflow details.

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
```text
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

## License

MIT License
