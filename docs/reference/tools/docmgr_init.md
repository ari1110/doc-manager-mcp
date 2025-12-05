# Initialize documentation manager

**Tool:** `docmgr_init`

Initialize doc-manager for a project (existing docs or create new).

## Purpose

Sets up doc-manager infrastructure in your project by creating configuration files and baseline tracking. Supports both existing documentation and new documentation bootstrapping.

## When to use

- First-time setup of doc-manager in a project
- Before using any other doc-manager tools
- When starting documentation from scratch (bootstrap mode)
- When adding doc-manager to existing documentation (existing mode)

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |
| `mode` | string | No | `"existing"` | `"existing"` or `"bootstrap"` |
| `platform` | string | No | `null` | Doc platform: `mkdocs`, `sphinx`, `hugo`, `docusaurus`, etc. |
| `exclude_patterns` | list[string] | No | `null` | Glob patterns to exclude from tracking |
| `docs_path` | string | No | `null` | Path to docs directory (default: `docs`) |
| `sources` | list[string] | No | `null` | Glob patterns for source files to track |

## Output

```json
{
  "status": "success",
  "message": "Memory system initialized successfully",
  "baseline_path": "/project/.doc-manager/memory/repo-baseline.json",
  "conventions_path": "/project/.doc-manager/memory/doc-conventions.yml",
  "symbol_baseline_path": "/project/.doc-manager/memory/symbol-baseline.json",
  "repository": "my-project",
  "language": "Python",
  "docs_exist": true,
  "metadata": {
    "git_commit": "abc1234",
    "git_branch": "main"
  },
  "files_tracked": 133,
  "symbols_indexed": 268,
  "symbol_breakdown": {
    "function": 120,
    "class": 45,
    "method": 103
  }
}
```

### Output fields

| Field | Description |
|-------|-------------|
| `language` | Primary programming language detected |
| `docs_exist` | Whether documentation directory exists |
| `metadata.git_branch` | Current git branch at initialization |
| `files_tracked` | Total files included in repo baseline |
| `symbols_indexed` | Total code symbols indexed by TreeSitter |
| `symbol_breakdown` | Symbol counts by type (class, function, method, etc.) |

## Examples

### Initialize for existing documentation

```python
await mcp.call_tool("docmgr_init", {
  "project_path": "/path/to/project",
  "mode": "existing",
  "platform": "mkdocs",
  "sources": ["src/**/*.py"]
})
```

### Bootstrap new documentation

```python
await mcp.call_tool("docmgr_init", {
  "project_path": "/path/to/project",
  "mode": "bootstrap",
  "platform": "sphinx",
  "sources": ["lib/**/*.js", "packages/**/*.ts"]
})
```

### Initialize with exclusions

```python
await mcp.call_tool("docmgr_init", {
  "project_path": "/path/to/project",
  "mode": "existing",
  "exclude_patterns": [
    "tests/**",
    "**/__pycache__/**",
    "dist/**"
  ]
})
```

## Files created

- `.doc-manager.yml` - Main configuration file
- `.doc-manager/memory/repo-baseline.json` - File checksums
- `.doc-manager/memory/symbol-baseline.json` - TreeSitter symbol index
- `.doc-manager/dependencies.json` - Code-to-docs mappings
- `.doc-manager/memory/doc-conventions.yml` - Documentation standards

## Notes

- **Mode differences**:
  - `mode="existing"`: Only creates config and baselines (assumes docs already exist)
  - `mode="bootstrap"`: Creates documentation structure from templates plus config and baselines
- **Source patterns**: Must use glob syntax (`src/**/*.py`), not plain directory names like `src`
- **Platform detection**: If `platform` not specified, auto-detection will be attempted
- **Idempotent**: Safe to run multiple times (won't overwrite existing baselines)
- **Prerequisites**: Project must have git repository initialized

## Typical workflow

```text
1. Run docmgr_init once at project setup
2. Edit .doc-manager.yml to refine sources/excludes if needed
3. Proceed with other doc-manager tools (sync, validate, etc.)
```

## See also

- [Configuration reference](../file-formats.md#doc-manageryml)
- [docmgr_detect_platform](docmgr_detect_platform.md) - Auto-detect documentation platform
- [docmgr_sync](docmgr_sync.md) - Sync documentation with code changes
