# Documentation Manager MCP Server

An MCP (Model Context Protocol) server for comprehensive documentation lifecycle management. Automates documentation creation, maintenance, quality assessment, and synchronization for software projects.

**Version:** 1.1.0
**Architecture:** 7-tool design with clear separation of concerns

## Features

### 7-Tool Architecture

The server provides **7 core tools** organized into 4 tiers:

#### Tier 1: Setup & Initialization
- **`docmgr_init`** - Unified initialization (replaces: `initialize_config`, `initialize_memory`, `bootstrap`)
  - Mode `existing`: Initialize for projects with existing docs
  - Mode `bootstrap`: Create fresh documentation structure

#### Tier 2: Analysis & Read-Only Operations
- **`docmgr_detect_changes`** - Pure read-only change detection (never writes baselines)
- **`docmgr_detect_platform`** - Identify/recommend documentation platforms
- **`docmgr_validate_docs`** - Check for broken links, missing assets, invalid code snippets
- **`docmgr_assess_quality`** - Evaluate docs against 7 quality criteria

#### Tier 3: State Management
- **`docmgr_update_baseline`** - Atomically update all 3 baselines (repo, symbols, dependencies)
- **`docmgr_sync`** - Orchestrate change detection + validation + quality + baseline updates

#### Tier 4: Workflows & Orchestration
- **`docmgr_migrate`** - Restructure/migrate documentation

### Key Improvements (v1.1.0)

✨ **Unified Initialization** - Single entry point (`docmgr_init`) with modes
🔒 **Read-Only Guarantees** - `docmgr_detect_changes` never modifies baselines
⚛️ **Atomic Updates** - `docmgr_update_baseline` updates all baselines together
🔄 **Mode-Based Sync** - `docmgr_sync` supports `check` (read-only) and `resync` (update baselines)
📊 **Semantic Analysis** - TreeSitter-based code symbol tracking
🗺️ **Dependency Tracking** - Automatic code-to-docs mapping

## Installation

```bash
# Using pip
pip install doc-manager-mcp

# Or from source
git clone https://github.com/yourusername/doc-manager
cd doc-manager
pip install -e .
```

## Quick Start

### 1. Initialize for Existing Project

```python
# For projects that already have documentation
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "existing",
    "docs_path": "docs"
  }
}
```

This creates:
- `.doc-manager.yml` configuration
- `.doc-manager/memory/` baselines (repo, symbols)
- `.doc-manager/dependencies.json` code-to-docs mappings

### 2. Bootstrap New Documentation

```python
# For projects without documentation
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "bootstrap",
    "docs_path": "docs"
  }
}
```

This creates documentation structure + config + baselines.

### 3. Detect Changes (Read-Only)

```python
{
  "tool": "docmgr_detect_changes",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "checksum",
    "include_semantic": true
  }
}
```

**Key feature:** NEVER writes to baselines (pure read-only).

### 4. Sync Documentation

```python
# Check mode (read-only analysis)
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "check",
    "docs_path": "docs"
  }
}

# Resync mode (analysis + update baselines)
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "resync",
    "docs_path": "docs"
  }
}
```

### 5. Update Baselines

```python
# After updating docs, refresh all baselines
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project",
    "docs_path": "docs"
  }
}
```

Updates 3 files atomically:
- `repo-baseline.json` (file checksums)
- `symbol-baseline.json` (code symbols via TreeSitter)
- `dependencies.json` (code-to-docs mappings)

## Tool Reference

### docmgr_init

**Purpose:** Unified initialization (Tier 1)
**Replaces:** `docmgr_initialize_config`, `docmgr_initialize_memory`, `docmgr_bootstrap`

**Parameters:**
- `project_path` (required): Absolute path to project root
- `mode` (required): `"existing"` or `"bootstrap"`
- `platform` (optional): Documentation platform (auto-detected if omitted)
- `exclude_patterns` (optional): Additional patterns to exclude
- `docs_path` (optional): Documentation directory (default: `"docs"`)
- `sources` (optional): Source directories to track

**Example:**
```json
{
  "project_path": "/home/user/myproject",
  "mode": "existing",
  "docs_path": "documentation"
}
```

### docmgr_detect_changes

**Purpose:** Pure read-only change detection (Tier 2)
**Key Guarantee:** NEVER writes to baselines

**Parameters:**
- `project_path` (required): Absolute path to project root
- `mode` (optional): `"checksum"` (default) or `"git_diff"`
- `since_commit` (optional): Git commit SHA for `git_diff` mode
- `include_semantic` (optional): Include TreeSitter symbol analysis (default: `false`)

**Example:**
```json
{
  "project_path": "/home/user/myproject",
  "mode": "checksum",
  "include_semantic": true
}
```

**Returns:**
```json
{
  "status": "success",
  "changes_detected": true,
  "total_changes": 3,
  "changed_files": [
    {"file": "src/main.py", "category": "source"},
    {"file": "src/utils.py", "category": "source"}
  ],
  "affected_documentation": ["docs/api.md"],
  "semantic_changes": [...],
  "note": "Read-only detection - baselines NOT updated"
}
```

### docmgr_update_baseline

**Purpose:** Atomically update all baselines (Tier 3)

**Parameters:**
- `project_path` (required): Absolute path to project root
- `docs_path` (optional): Documentation directory

**Example:**
```json
{
  "project_path": "/home/user/myproject",
  "docs_path": "docs"
}
```

### docmgr_sync

**Purpose:** Orchestrated documentation sync (Tier 4)

**Parameters:**
- `project_path` (required): Absolute path to project root
- `mode` (required): `"check"` (read-only) or `"resync"` (update baselines)
- `docs_path` (optional): Documentation directory

**Modes:**
- `check`: Detects changes, validates docs, assesses quality (read-only)
- `resync`: Does everything `check` does + updates baselines atomically

**Example:**
```json
{
  "project_path": "/home/user/myproject",
  "mode": "resync",
  "docs_path": "docs"
}
```

### Other Tools

- **`docmgr_detect_platform`** - Auto-detect documentation platform
- **`docmgr_validate_docs`** - Check links, assets, code snippets
- **`docmgr_assess_quality`** - Evaluate against 7 quality criteria
- **`docmgr_migrate`** - Restructure documentation

See [API Reference](docs/api-reference.md) for complete documentation.

## Migration from v1.0.x

### Deprecated Tools (v1.1.0)

The following tools were **removed in v2.0.0**:

| Removed Tool | Use Instead | Notes |
|----------------|-------------|-------|
| `docmgr_initialize_config` | `docmgr_init` with `mode="existing"` | Unified initialization |
| `docmgr_initialize_memory` | `docmgr_init` with `mode="existing"` | Unified initialization |
| `docmgr_bootstrap` | `docmgr_init` with `mode="bootstrap"` | Unified initialization |
| `docmgr_map_changes` | `docmgr_detect_changes` or `docmgr_sync` | Read-only detection |

> **Note:** If you need backward compatibility with v1.0.x tools, use v1.1.0. See [MIGRATION.md](MIGRATION.md) for details.

### Migration Steps (v1.0.x → v2.0.0)

1. **Replace initialization calls:**
   ```python
   # OLD (removed in v2.0)
   await docmgr_initialize_config(...)
   await docmgr_initialize_memory(...)

   # NEW (v2.0.0)
   await docmgr_init(project_path="...", mode="existing")
   ```

2. **Replace change detection:**
   ```python
   # OLD (removed in v2.0 - wrote to baselines)
   await docmgr_map_changes(...)

   # NEW (v2.0.0 - read-only)
   await docmgr_detect_changes(...)
   ```

3. **Use explicit baseline updates:**
   ```python
   # After updating docs (v2.0.0)
   await docmgr_update_baseline(project_path="...", docs_path="docs")
   ```

4. **Use mode-based sync:**
   ```python
   # Read-only analysis
   await docmgr_sync(project_path="...", mode="check")

   # Analysis + update baselines
   await docmgr_sync(project_path="...", mode="resync")
   ```

See [MIGRATION.md](MIGRATION.md) for detailed migration guide.

## Project Structure

```
doc-manager/
├── doc_manager_mcp/
│   ├── server.py              # Main MCP server
│   ├── constants.py           # Enums and constants
│   ├── models.py              # Pydantic input models
│   ├── utils.py               # Utility functions
│   ├── tools/
│   │   ├── init.py            # Unified initialization (NEW)
│   │   ├── detect_changes.py # Read-only change detection (NEW)
│   │   ├── update_baseline.py# Baseline management (NEW)
│   │   ├── workflows.py       # Sync, migrate, bootstrap
│   │   ├── validation.py      # Link/asset validation
│   │   ├── quality.py         # Quality assessment
│   │   ├── platform.py        # Platform detection
│   │   ├── dependencies.py    # Dependency tracking
│   │   ├── config.py          # Config management (deprecated)
│   │   ├── memory.py          # Memory system (deprecated)
│   │   └── changes.py         # map_changes (deprecated)
│   └── indexing/
│       ├── tree_sitter.py     # Code symbol indexing
│       ├── semantic_diff.py   # Symbol comparison
│       └── baseline.py        # Baseline management
├── tests/
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── specs/                     # Technical specifications
├── pyproject.toml
└── README.md
```

## Configuration

Example `.doc-manager.yml`:

```yaml
platform: mkdocs
exclude:
  - '**/node_modules'
  - '**/dist'
  - '**/.venv'
  - '**/__pycache__'
docs_path: docs
sources:
  - src
  - lib
metadata:
  language: Python
  created: '2025-01-19T20:00:00'
  version: '1.1.0'
```

## Memory System

### Baselines

1. **`repo-baseline.json`** - File checksums and metadata
2. **`symbol-baseline.json`** - TreeSitter code symbols (functions, classes, etc.)
3. **`dependencies.json`** - Code-to-docs dependency mappings

### Baseline Workflow

```
1. docmgr_init              → Create initial baselines
2. (make code changes)
3. docmgr_detect_changes    → Detect changes (read-only)
4. (update documentation)
5. docmgr_update_baseline   → Refresh baselines
```

Or use `docmgr_sync` with `mode="resync"` for steps 3-5 combined.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=doc_manager_mcp
```

### Running the Server

```bash
# Install in development mode
pip install -e .

# Run server (stdio transport)
doc-manager
```

### Adding New Tools

1. Create tool implementation in `doc_manager_mcp/tools/`
2. Define Pydantic input model in `doc_manager_mcp/models.py`
3. Register tool in `doc_manager_mcp/server.py` with `@mcp.tool` decorator
4. Add tests in `tests/unit/` and `tests/integration/`
5. Update this README and API reference

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Follow the 7-tool architecture principles
2. Maintain clear separation of concerns (tiers 1-4)
3. Add tests for new functionality
4. Update documentation

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/doc-manager/issues)
- **Spec Docs:** See `specs/` directory for technical specifications
- **API Reference:** See [docs/api-reference.md](docs/api-reference.md)
