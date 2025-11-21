# Basic usage

This guide covers common workflows and use cases for Documentation Manager.

## Workflow 1: Setting up a new project

### Step 1: Detect platform

Identify the best documentation platform for your project:

```json
{
  "tool": "docmgr_detect_platform",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Returns platform recommendation (e.g., MkDocs for Python, Hugo for Go).

### Step 2: Bootstrap documentation

Create documentation structure from scratch:

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "bootstrap",
    "docs_path": "docs",
    "sources": ["src/**/*.py"]
  }
}
```

This creates 6 documentation files, configuration, and baselines.

## Workflow 2: Managing existing documentation

### Detect changes

Check what code has changed since last baseline:

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

This is **read-only** and never modifies baselines.

### Validate documentation

Check for broken links, missing assets, and code snippet issues:

```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "project_path": "/path/to/project",
    "docs_path": "docs",
    "check_links": true,
    "check_assets": true,
    "check_snippets": true
  }
}
```

Returns detailed issues with file locations and line numbers.

### Assess quality

Evaluate documentation quality across 7 criteria:

```json
{
  "tool": "docmgr_assess_quality",
  "arguments": {
    "project_path": "/path/to/project",
    "docs_path": "docs"
  }
}
```

Returns overall score (excellent, good, fair, needs_improvement) and specific findings.

## Workflow 3: Keeping docs in sync

### Check sync status

Analyze current state without making changes:

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "check"
  }
}
```

This runs:
1. Change detection
2. Documentation validation
3. Quality assessment
4. Recommendations

### Update baselines

After updating docs to reflect code changes:

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "resync"
  }
}
```

This updates all 3 baseline files atomically:
- `repo-baseline.json` (file checksums)
- `symbol-baseline.json` (code symbols)
- `dependencies.json` (code-to-docs mappings)

## Workflow 4: Migrating documentation

Restructure or migrate documentation with git history preservation:

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "project_path": "/path/to/project",
    "source_path": "old-docs",
    "target_path": "docs",
    "preserve_history": true,
    "rewrite_links": true
  }
}
```

## Understanding baselines

Documentation Manager tracks three types of baselines:

1. **Repo baseline** (`repo-baseline.json`) - File checksums for all tracked files
2. **Symbol baseline** (`symbol-baseline.json`) - TreeSitter-extracted code symbols (classes, functions, methods)
3. **Dependencies** (`dependencies.json`) - Mappings between code symbols and documentation files

These baselines enable intelligent change detection and impact analysis.

## Best practices

### Use glob patterns in sources

Always specify **glob patterns** in `.doc-manager.yml`:

```yaml
sources:
  - "src/**/*.py"           # ✓ Correct
  - "lib/**/*.{js,ts}"      # ✓ Correct with multiple extensions
```

Not:

```yaml
sources:
  - "src"                   # ✗ Won't work - needs glob pattern
```

### Choose the right sync mode

- **check mode**: Use for analysis without modifying baselines
- **resync mode**: Use after updating docs to update baselines

### Validate before committing

Run validation and quality assessment before committing documentation changes:

```bash
# In your pre-commit workflow
docmgr_validate_docs && docmgr_assess_quality
```

## Troubleshooting

### Empty symbol baseline

If `symbol-baseline.json` has no symbols:

1. Check `.doc-manager.yml` has correct glob patterns in `sources`
2. Ensure patterns match your source files (e.g., `"src/**/*.py"`)
3. Run `docmgr_update_baseline` to regenerate

### Validation errors

Common validation issues:

- **Code block missing language** - Add language specifier (e.g., ` ```python`)
- **Broken links** - Check relative paths and file existence
- **Missing alt text** - Add descriptive alt text to images
