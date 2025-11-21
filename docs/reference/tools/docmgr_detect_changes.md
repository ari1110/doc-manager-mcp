# docmgr_detect_changes

Detect code changes without modifying baselines (pure read-only).

## Purpose

Identifies changed files by comparing current state against baselines. Categorizes changes and maps them to affected documentation. Provides semantic change detection for symbol-level modifications.

## When to use

- After code changes to check if documentation is out of sync
- Before deciding whether to update documentation or baselines
- To identify which docs may need updates
- As part of CI/CD to detect doc drift

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |
| `since_commit` | string | No | `null` | Git commit hash for git_diff mode |
| `mode` | string | No | `"checksum"` | `"checksum"` or `"git_diff"` |
| `include_semantic` | bool | No | `false` | Enable symbol-level change detection |

## Output

```json
{
  "changes_detected": true,
  "changed_files": {
    "code": ["src/api.py", "src/models.py"],
    "documentation": ["docs/api.md"],
    "asset": [],
    "config": [".doc-manager.yml"]
  },
  "affected_docs": {
    "docs/api.md": ["src/api.py"],
    "docs/reference.md": ["src/models.py"]
  },
  "semantic_changes": {
    "added": ["new_function"],
    "modified": ["existing_class"],
    "deleted": ["old_method"]
  }
}
```

## Examples

### Basic change detection (checksum mode)

```python
await mcp.call_tool("docmgr_detect_changes", {
  "project_path": "/path/to/project",
  "mode": "checksum"
})
```

### Semantic change detection

```python
await mcp.call_tool("docmgr_detect_changes", {
  "project_path": "/path/to/project",
  "mode": "checksum",
  "include_semantic": true
})
```

### Compare against specific commit

```python
await mcp.call_tool("docmgr_detect_changes", {
  "project_path": "/path/to/project",
  "mode": "git_diff",
  "since_commit": "abc123def456"
})
```

## Change categories

Changes are categorized as:

- **code**: Source files matching `sources` patterns
- **documentation**: Files in `docs_path`
- **asset**: Images, PDFs, media files
- **config**: Configuration files (`.doc-manager.yml`, etc.)
- **dependency**: Package files (package.json, requirements.txt, etc.)
- **test**: Test files
- **infrastructure**: CI/CD, Docker, deployment files
- **other**: Everything else

## Notes

- **Read-only**: This tool NEVER modifies baselines (unlike `docmgr_sync` with `mode="resync"`)
- **Modes**:
  - `checksum`: Compare current file checksums against `repo-baseline.json`
  - `git_diff`: Compare current files against a specific git commit
- **Semantic detection**: When `include_semantic=true`, detects function/class additions, modifications, and deletions using TreeSitter
- **Performance**: Semantic detection is slower due to AST parsing
- **Prerequisites**: Requires baselines to exist (run `docmgr_init` first)

## Typical workflow

```
1. Make code changes
2. Run docmgr_detect_changes to see what changed
3. Review affected_docs to identify which docs need updates
4. Update documentation
5. Run docmgr_update_baseline or docmgr_sync mode="resync"
```

## See also

- [docmgr_update_baseline](docmgr_update_baseline.md) - Update baselines after doc changes
- [docmgr_sync](docmgr_sync.md) - Full sync with optional baseline update
- [Baseline files reference](../file-formats.md#doc-managermemoryrepo-baselinejson)
