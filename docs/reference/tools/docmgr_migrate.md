# docmgr_migrate

Migrate or restructure documentation while optionally preserving git history.

## Purpose

Moves or restructures documentation files with support for git history preservation, link rewriting, and table of contents regeneration. Supports platform migration and directory reorganization.

## When to use

- Moving docs to a new location in the repository
- Changing documentation platform (e.g., Sphinx → MkDocs)
- Reorganizing documentation structure
- Consolidating multiple doc directories
- Migrating from unstructured to structured documentation

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |
| `source_path` | string | Yes | - | Source documentation directory |
| `target_path` | string | No | `"docs"` | Target documentation directory |
| `target_platform` | string | No | `null` | Target platform (mkdocs, sphinx, etc.) |
| `preserve_history` | bool | No | `true` | Use git mv to maintain file history |
| `rewrite_links` | bool | No | `false` | Update internal links to match new structure |
| `regenerate_toc` | bool | No | `false` | Rebuild table of contents |
| `dry_run` | bool | No | `false` | Preview changes without executing |

## Output

```json
{
  "status": "success",
  "files_migrated": 45,
  "links_rewritten": 127,
  "toc_regenerated": true,
  "history_preserved": true,
  "operations": [
    {
      "type": "move",
      "from": "old-docs/guide.md",
      "to": "docs/guides/guide.md",
      "preserved_history": true
    },
    {
      "type": "rewrite_links",
      "file": "docs/index.md",
      "changes": 5
    }
  ],
  "warnings": [
    "3 external links may need manual review"
  ]
}
```

### Dry run output

```json
{
  "status": "dry_run",
  "would_migrate": 45,
  "would_rewrite_links": 127,
  "operations_planned": [
    "Move old-docs/guide.md → docs/guides/guide.md (preserve history)",
    "Rewrite 5 links in docs/index.md",
    "Regenerate table of contents"
  ],
  "warnings": [
    "Source contains 3 broken links that will carry over"
  ]
}
```

## Examples

### Preview migration (dry run)

```python
await mcp.call_tool("docmgr_migrate", {
  "project_path": "/path/to/project",
  "source_path": "old-docs",
  "target_path": "docs",
  "dry_run": true
})
```

### Simple migration with history

```python
await mcp.call_tool("docmgr_migrate", {
  "project_path": "/path/to/project",
  "source_path": "documentation",
  "target_path": "docs",
  "preserve_history": true
})
```

### Full migration with link rewriting

```python
await mcp.call_tool("docmgr_migrate", {
  "project_path": "/path/to/project",
  "source_path": "old-docs",
  "target_path": "docs",
  "target_platform": "mkdocs",
  "preserve_history": true,
  "rewrite_links": true,
  "regenerate_toc": true
})
```

### Platform migration

```python
await mcp.call_tool("docmgr_migrate", {
  "project_path": "/path/to/project",
  "source_path": "sphinx-docs",
  "target_path": "docs",
  "target_platform": "docusaurus",
  "rewrite_links": true,
  "regenerate_toc": true
})
```

## Migration process

1. **Validation**: Checks source exists, target doesn't conflict
2. **Analysis**: Scans links, assets, structure
3. **Planning**: Creates operation plan
4. **Execution** (unless dry_run):
   - Move files (git mv if preserve_history)
   - Rewrite links if requested
   - Regenerate TOC if requested
   - Update asset references
5. **Verification**: Confirms all files moved correctly

## Options explained

### `preserve_history` (default: true)

Uses `git mv` instead of regular file moves to maintain git history.

**Pros**: File history preserved in git blame/log
**Cons**: Requires clean git working directory

### `rewrite_links` (default: false)

Updates internal markdown links to match new structure.

**Example**: `[guide](../old-path/guide.md)` → `[guide](guides/guide.md)`

**Note**: Only rewrites internal links; external links unchanged

### `regenerate_toc` (default: false)

Rebuilds table of contents based on new structure.

**When useful**: Platform migration, major reorganization

### `dry_run` (default: false)

Shows what would happen without making changes.

**Always use dry_run first** to preview migration plan.

## Notes

- **State-modifying**: Creates/moves files, modifies content (unless dry_run)
- **Git requirement**: `preserve_history` requires git repository
- **Clean working directory**: Git operations require no uncommitted changes
- **Backup recommended**: Run dry_run first, consider backing up source
- **Platform-specific**: Some platform migrations may require manual config updates
- **Link rewriting**: Internal links only; external links and anchors may need manual review

## Typical workflow

```text
1. Run with dry_run=true to preview migration
2. Review planned operations and warnings
3. Commit any uncommitted changes (if preserve_history)
4. Run migration with dry_run=false
5. Verify migrated documentation
6. Update .doc-manager.yml if needed
7. Run docmgr_update_baseline to refresh baselines
```

## See also

- [docmgr_init](docmgr_init.md) - Initialize doc-manager after migration
- [docmgr_validate_docs](docmgr_validate_docs.md) - Validate after migration
- [Platform support guide](../../guides/platforms.md)
