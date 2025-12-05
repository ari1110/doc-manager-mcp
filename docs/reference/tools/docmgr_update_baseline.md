# Update baseline

**Tool:** `docmgr_update_baseline`

Update all baseline files to reflect current project state.

## Purpose

Atomically updates all three baseline files (repo-baseline.json, symbol-baseline.json, dependencies.json) to capture current state. Resets change detection to treat current state as the new "clean" baseline.

## When to use

- After updating documentation to match code changes
- When documentation is in sync with code and you want to reset baseline
- After fixing validation issues
- To establish a new baseline after major refactoring

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |
| `docs_path` | string | No | `null` | Override docs path from config |

## Output

```json
{
  "status": "success",
  "message": "All baselines updated successfully",
  "updated_files": ["repo-baseline.json", "symbol-baseline.json", "dependencies.json"],
  "details": {
    "repo_baseline": {
      "status": "success",
      "files_tracked": 133,
      "language": "Python",
      "docs_exist": true,
      "git_commit": "abc1234...",
      "git_branch": "main",
      "path": "/project/.doc-manager/memory/repo-baseline.json"
    },
    "symbol_baseline": {
      "status": "success",
      "symbols_tracked": 268,
      "breakdown": {
        "function": 120,
        "class": 45,
        "method": 103
      },
      "path": "/project/.doc-manager/memory/symbol-baseline.json"
    },
    "dependencies": {
      "status": "success",
      "total_references": 744,
      "total_doc_files": 28,
      "total_source_files": 47,
      "unmatched_references": 12,
      "path": "/project/.doc-manager/dependencies.json"
    }
  }
}
```

### Output fields

| Field | Description |
|-------|-------------|
| `details.repo_baseline.language` | Primary programming language detected |
| `details.repo_baseline.docs_exist` | Whether documentation directory exists |
| `details.repo_baseline.git_branch` | Current git branch |
| `details.symbol_baseline.breakdown` | Symbol counts by type (class, function, method, etc.) |
| `details.dependencies.total_doc_files` | Number of documentation files with code references |
| `details.dependencies.total_source_files` | Number of source files referenced by docs |
| `details.dependencies.unmatched_references` | References in docs that don't match real files |

## Examples

### Update baselines after doc changes

```python
await mcp.call_tool("docmgr_update_baseline", {
  "project_path": "/path/to/project"
})
```

### Update with custom docs path

```python
await mcp.call_tool("docmgr_update_baseline", {
  "project_path": "/path/to/project",
  "docs_path": "documentation"
})
```

## Files updated

All three baseline files are updated atomically:

1. **`.doc-manager/memory/repo-baseline.json`**
   - Updated file checksums (SHA-256)
   - Current git commit/branch metadata
   - File count and timestamp

2. **`.doc-manager/memory/symbol-baseline.json`**
   - Refreshed TreeSitter symbol index
   - Updated symbol counts by type
   - New generation timestamp

3. **`.doc-manager/dependencies.json`**
   - Rebuilt code-to-docs mappings
   - Refreshed doc-to-code mappings
   - Updated asset-to-docs mappings
   - New unmatched references

## Notes

- **Atomicity**: All three baselines update together (success or rollback)
- **State-modifying**: This tool rewrites baseline files
- **Idempotent**: Safe to run multiple times
- **Prerequisites**: Requires `.doc-manager.yml` to exist (run `docmgr_init` first)
- **When to avoid**: Don't run if documentation is still out of sync with code
- **Git integration**: Captures current git commit hash in metadata

## Typical workflow

```text
1. Detect changes with docmgr_detect_changes
2. Update documentation to match code changes
3. Run docmgr_update_baseline to reset baselines
4. Future change detection starts from new baseline
```

Alternative: Use `docmgr_sync mode="resync"` to combine detection + baseline update in one step.

## See also

- [docmgr_detect_changes](docmgr_detect_changes.md) - Detect changes before updating baselines
- [docmgr_sync](docmgr_sync.md) - Combined sync + baseline update
- [Baseline files reference](../file-formats.md)
