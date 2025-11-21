# Tools reference

Complete reference for all 8 Documentation Manager tools organized by tier.

## Tier 1: Setup & initialization

### docmgr_init

Initialize doc-manager for a project.

**Description**: Unified initialization tool that creates configuration, baselines, and optionally documentation structure.

**Parameters**:
- `project_path` (string, required) - Absolute path to project root
- `mode` (string, required) - Initialization mode: `"existing"` or `"bootstrap"`
- `platform` (string, optional) - Documentation platform (auto-detected if not specified)
- `exclude_patterns` (list[string], optional) - Glob patterns to exclude
- `docs_path` (string, optional) - Documentation directory path (default: `"docs"`)
- `sources` (list[string], optional) - Glob patterns for source files to track

**Modes**:
- `existing`: Initialize for projects with existing documentation
- `bootstrap`: Create fresh documentation structure from scratch

**Returns**:
```json
{
  "status": "success",
  "message": "...",
  "mode": "existing|bootstrap",
  "steps_completed": {
    "config": "created|completed",
    "memory": "created|completed",
    "dependencies": "created|completed"
  }
}
```

**Example**:
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

---

## Tier 2: Analysis & read-only operations

### docmgr_detect_changes

Detect code changes without modifying baselines (pure read-only).

**Description**: Compares current code state against baselines to identify changes. Never writes to baselines.

**Parameters**:
- `project_path` (string, required) - Absolute path to project root
- `since_commit` (string, optional) - Git commit hash to compare against
- `mode` (string, optional) - Detection mode: `"checksum"` or `"git_diff"` (default: `"checksum"`)
- `include_semantic` (bool, optional) - Include semantic symbol analysis (default: `false`)

**Modes**:
- `checksum`: Compare file checksums against `repo-baseline.json`
- `git_diff`: Compare against specific git commit

**Returns**:
```json
{
  "status": "success",
  "changes_detected": true|false,
  "total_changes": 0,
  "changed_files": [...],
  "affected_documentation": [...],
  "semantic_changes": [...],
  "note": "Read-only detection - baselines NOT updated"
}
```

**Example**:
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

### docmgr_detect_platform

Detect and recommend documentation platform for the project.

**Description**: Analyzes project characteristics to identify or recommend appropriate documentation platform.

**Parameters**:
- `project_path` (string, required) - Absolute path to project root

**Returns**:
```json
{
  "detected_platforms": [...],
  "recommendation": "mkdocs|sphinx|hugo|docusaurus|...",
  "rationale": [...],
  "project_language": "Python|JavaScript|Go|..."
}
```

**Example**:
```json
{
  "tool": "docmgr_detect_platform",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

### docmgr_validate_docs

Validate documentation for broken links, missing assets, and code snippet issues.

**Description**: Performs comprehensive validation checks on documentation files with convention enforcement.

**Parameters**:
- `project_path` (string, required) - Absolute path to project root
- `docs_path` (string, optional) - Documentation directory path
- `check_links` (bool, optional) - Check for broken links (default: `true`)
- `check_assets` (bool, optional) - Check for missing assets (default: `true`)
- `check_snippets` (bool, optional) - Check code snippet validity (default: `true`)
- `validate_code_syntax` (bool, optional) - Validate code block syntax (default: `false`)
- `validate_symbols` (bool, optional) - Validate code symbols exist (default: `false`)

**Returns**:
```json
{
  "total_issues": 6,
  "errors": 1,
  "warnings": 5,
  "issues": [
    {
      "type": "convention|syntax_error|broken_link|...",
      "severity": "error|warning",
      "file": "index.md",
      "line": 15,
      "rule": "block_language_required",
      "message": "..."
    }
  ]
}
```

**Example**:
```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "project_path": "/path/to/project",
    "docs_path": "docs",
    "check_links": true,
    "check_assets": true
  }
}
```

### docmgr_assess_quality

Assess documentation quality against 7 criteria.

**Description**: Evaluates documentation across relevance, accuracy, purposefulness, uniqueness, consistency, clarity, and structure.

**Parameters**:
- `project_path` (string, required) - Absolute path to project root
- `docs_path` (string, optional) - Documentation directory path
- `criteria` (list[string], optional) - Specific criteria to assess (default: all 7)

**Criteria**:
- `relevance`: Documentation relevance to current codebase
- `accuracy`: Code examples and API references accuracy
- `purposefulness`: Clear purpose and audience
- `uniqueness`: Avoids duplication and redundancy
- `consistency`: Consistent style and formatting
- `clarity`: Clear and understandable language
- `structure`: Logical organization and navigation

**Returns**:
```json
{
  "assessed_at": "2025-11-20T20:26:41",
  "overall_score": "excellent|good|fair|needs_improvement",
  "criteria": [
    {
      "criterion": "relevance",
      "score": "good",
      "findings": [...],
      "issues": [...],
      "metrics": {...}
    }
  ],
  "coverage": {
    "total_symbols": 20702,
    "documented_symbols": 22,
    "coverage_percentage": 0.1
  }
}
```

**Example**:
```json
{
  "tool": "docmgr_assess_quality",
  "arguments": {
    "project_path": "/path/to/project",
    "docs_path": "docs"
  }
}
```

---

## Tier 3: State management

### docmgr_update_baseline

Update all baseline files atomically.

**Description**: Updates three baselines: repo-baseline.json (file checksums), symbol-baseline.json (code symbols), and dependencies.json (code-to-docs mappings).

**Parameters**:
- `project_path` (string, required) - Absolute path to project root
- `docs_path` (string, optional) - Documentation directory path

**Returns**:
```json
{
  "status": "success",
  "message": "All baselines updated successfully",
  "updated_files": [
    "repo-baseline.json",
    "symbol-baseline.json",
    "dependencies.json"
  ],
  "details": {
    "repo_baseline": {...},
    "symbol_baseline": {...},
    "dependencies": {...}
  }
}
```

**Example**:
```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project",
    "docs_path": "docs"
  }
}
```

### docmgr_sync

Sync documentation with code changes, identifying what needs updates.

**Description**: Orchestrates change detection, validation, quality assessment, and optional baseline updates.

**Parameters**:
- `project_path` (string, required) - Absolute path to project root
- `mode` (string, optional) - Sync mode: `"check"` or `"resync"` (default: `"check"`)
- `docs_path` (string, optional) - Documentation directory path

**Modes**:
- `check`: Read-only analysis (no baseline updates)
- `resync`: Full sync with atomic baseline updates

**Returns**:
```json
{
  "status": "success",
  "message": "...",
  "mode": "check|resync",
  "report": "# Markdown report...",
  "changes": 0,
  "affected_docs": 0,
  "recommendations": [...],
  "validation_issues": 6,
  "quality_score": "good",
  "baseline_updated": true|false|null
}
```

**Example**:
```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "resync"
  }
}
```

---

## Tier 4: Workflows & orchestration

### docmgr_migrate

Migrate existing documentation to new structure with optional git history preservation.

**Description**: Restructure or migrate documentation with link rewriting and git history preservation.

**Parameters**:
- `project_path` (string, required) - Absolute path to project root
- `source_path` (string, required) - Source documentation directory
- `target_path` (string, optional) - Target documentation directory (default: `"docs"`)
- `target_platform` (string, optional) - Target platform (auto-detected if not specified)
- `preserve_history` (bool, optional) - Preserve git history (default: `true`)
- `rewrite_links` (bool, optional) - Rewrite links to new paths (default: `false`)
- `regenerate_toc` (bool, optional) - Regenerate table of contents (default: `false`)
- `dry_run` (bool, optional) - Preview changes without applying (default: `false`)

**Returns**:
```json
{
  "status": "success",
  "message": "...",
  "files_migrated": 15,
  "links_rewritten": 42,
  "history_preserved": true
}
```

**Example**:
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

---

## Common workflows

### Initial setup workflow

1. `docmgr_detect_platform` - Identify platform
2. `docmgr_init` (mode=bootstrap) - Create documentation
3. Configure `.doc-manager.yml` with glob patterns
4. `docmgr_sync` (mode=resync) - Update baselines

### Maintenance workflow

1. Make code changes
2. `docmgr_sync` (mode=check) - Analyze impact
3. Update affected documentation
4. `docmgr_validate_docs` - Check for issues
5. `docmgr_assess_quality` - Evaluate quality
6. `docmgr_sync` (mode=resync) - Update baselines

### Migration workflow

1. `docmgr_migrate` (dry_run=true) - Preview migration
2. Review proposed changes
3. `docmgr_migrate` - Execute migration
4. `docmgr_init` (mode=existing) - Initialize for new structure
5. `docmgr_validate_docs` - Verify migration

---

## Error handling

All tools return structured error responses:

```json
{
  "status": "error",
  "message": "Descriptive error message"
}
```

Common errors:
- Project path does not exist
- .doc-manager not initialized (run docmgr_init first)
- Invalid configuration
- Baseline files missing or corrupted
