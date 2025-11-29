# Workflows

Common workflows and patterns for using doc-manager effectively.

> **Using Claude Code?** The [plugin](claude-code-plugin.md) provides agents and quick commands (`/doc-status`, `/doc-sync`, `/doc-quality`) that handle these workflows for you. The patterns below are for direct MCP tool usage in automation, CI/CD, or other clients.

## Initial setup workflow

Set up doc-manager in a new or existing project.

### For new projects (bootstrap)

**When to use**: Starting documentation from scratch

1. **Detect platform** (optional but recommended)

```json
{
  "tool": "docmgr_detect_platform",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Returns platform recommendation based on project language and structure (e.g., MkDocs for Python, Hugo for Go).

2. **Bootstrap documentation**

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "bootstrap",
    "platform": "mkdocs",
    "docs_path": "docs",
    "sources": ["src/**/*.py"],
    "exclude_patterns": ["tests/**", "**/__pycache__/**"]
  }
}
```

Creates documentation structure with templates, configuration (`.doc-manager.yml`), and baseline files.

3. **Review and customize**

- Edit `.doc-manager.yml` to refine source patterns and exclusions
- Customize `.doc-manager/memory/doc-conventions.yml` for your team's standards
- Fill in generated documentation templates

### For existing projects

**When to use**: Adding doc-manager to project with documentation already in place

1. **Initialize for existing docs**

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "existing",
    "platform": "mkdocs",
    "sources": ["src/**/*.py", "lib/**/*.ts"],
    "exclude_patterns": ["dist/**", "node_modules/**"]
  }
}
```

Creates configuration and baselines without modifying existing documentation.

2. **Validate existing documentation**

```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Identify any pre-existing issues (broken links, missing assets, syntax errors).

3. **Assess quality baseline**

```json
{
  "tool": "docmgr_assess_quality",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Establish quality baseline to track improvements over time.

---

## Daily maintenance workflow

Keep documentation in sync with code changes.

### After making code changes

1. **Check what changed**

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

Returns changed files categorized by type (code, docs, assets, etc.) and lists affected documentation.

**Read-only**: Does not modify baselines.

2. **Review affected documentation**

Based on `affected_docs` in the response, update documentation files that reference changed code.

3. **Validate changes**

```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "project_path": "/path/to/project",
    "check_links": true,
    "check_assets": true,
    "check_snippets": true
  }
}
```

Catch broken links, syntax errors, or convention violations introduced by changes.

4. **Update baselines**

After fixing documentation to match code changes:

```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Resets baselines to current state. Future change detection starts from this point.

### Automated sync workflow (shortcut)

Combine steps 1, 3, and 4 using `docmgr_sync`:

**Check mode** (read-only analysis):

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "check"
  }
}
```

Runs change detection, validation, and quality assessment without modifying baselines.

**Resync mode** (analysis + baseline update):

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "resync"
  }
}
```

Same as check mode but atomically updates all three baselines at the end.

**When to use each**:
- `mode="check"`: After code changes to see documentation impact
- `mode="resync"`: After updating documentation to reset baselines

---

## Quality improvement workflow

Systematically improve documentation quality.

1. **Run quality assessment**

```json
{
  "tool": "docmgr_assess_quality",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Returns scores for 7 criteria: relevance, accuracy, purposefulness, uniqueness, consistency, clarity, structure.

2. **Review findings**

Focus on criteria with "poor" or "fair" scores. Each criterion includes:
- Specific issues found
- Positive findings
- Actionable recommendations
- Metrics (e.g., API coverage %, duplicate topics count)

3. **Address high-priority issues**

Common improvements:
- **Low accuracy**: Document more public APIs, update outdated examples
- **Poor uniqueness**: Consolidate duplicate content
- **Fair consistency**: Standardize heading case, terminology
- **Clarity issues**: Add language tags to code blocks, simplify complex sentences

4. **Re-assess to track progress**

Run `docmgr_assess_quality` again after changes to measure improvement.

---

## Migration workflow

Restructure or move documentation while preserving git history.

### Planning migration

1. **Preview with dry run**

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "project_path": "/path/to/project",
    "source_path": "old-docs",
    "target_path": "docs",
    "preserve_history": true,
    "rewrite_links": true,
    "dry_run": true
  }
}
```

Shows what would happen without making changes. Review planned operations and warnings.

### Executing migration

2. **Run migration**

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "project_path": "/path/to/project",
    "source_path": "old-docs",
    "target_path": "docs",
    "target_platform": "mkdocs",
    "preserve_history": true,
    "rewrite_links": true,
    "regenerate_toc": true
  }
}
```

**Note**: Requires clean git working directory if `preserve_history=true`.

3. **Validate migrated docs**

```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Verify no broken links or issues from migration.

4. **Update configuration**

If changing platforms, update `.doc-manager.yml`:

```yaml
platform: mkdocs  # Update to new platform
docs_path: docs   # Update to new path
```

5. **Reset baselines**

```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

---

## CI/CD integration workflow

Automate documentation checks in your pipeline.

### Pre-commit validation

Run validation before allowing commits:

```bash
#!/bin/bash
# .git/hooks/pre-commit

result=$(docmgr_validate_docs --project-path .)
issues=$(echo "$result" | jq '.total_issues')

if [ "$issues" -gt 0 ]; then
  echo "Documentation validation failed with $issues issues"
  exit 1
fi
```

### Pull request checks

Detect if documentation is out of sync with code:

```yaml
# .github/workflows/doc-check.yml
name: Documentation Check

on: [pull_request]

jobs:
  check-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check doc sync
        run: |
          result=$(docmgr_sync --mode check)
          changes=$(echo "$result" | jq '.changes.detected')

          if [ "$changes" == "true" ]; then
            echo "Documentation out of sync with code changes"
            exit 1
          fi
```

### Release quality gate

Enforce documentation quality before releases:

```bash
#!/bin/bash
# scripts/check-docs-quality.sh

result=$(docmgr_assess_quality --project-path .)
score=$(echo "$result" | jq -r '.overall_score')

if [ "$score" == "poor" ]; then
  echo "Documentation quality too low for release"
  exit 1
fi

echo "Documentation quality: $score"
```

---

## Understanding baselines

Doc-manager uses three baseline files to track state:

### 1. Repo baseline (`.doc-manager/memory/repo-baseline.json`)

**Purpose**: File checksums for change detection

**Contains**:
- SHA-256 checksum for each tracked file
- Git commit/branch metadata
- Timestamp of last update

**Updated by**:
- `docmgr_init` (initial creation)
- `docmgr_update_baseline` (manual update)
- `docmgr_sync mode="resync"` (automatic update)

### 2. Symbol baseline (`.doc-manager/memory/symbol-baseline.json`)

**Purpose**: TreeSitter index of code symbols

**Contains**:
- Classes, functions, methods with locations
- Symbol metadata (public/private, parameters, etc.)
- File-to-symbol mappings

**Used for**:
- Semantic change detection (`include_semantic=true`)
- Symbol existence validation (`validate_symbols=true`)
- API coverage metrics

### 3. Dependencies (`.doc-manager/dependencies.json`)

**Purpose**: Code-to-docs and docs-to-code mappings

**Contains**:
- `doc_to_code`: Which docs reference which source files
- `code_to_doc`: Which source files are documented where
- `asset_to_docs`: Which assets are used in which docs
- `unmatched_references`: Code references that couldn't be matched

**Used for**:
- Identifying affected docs when code changes
- Finding undocumented code
- Tracking asset usage

---

## Best practices

### Configure source patterns correctly

**Always use glob patterns** in `.doc-manager.yml`:

```yaml
sources:
  - "src/**/*.py"           # ✓ Matches all .py files recursively
  - "lib/**/*.{js,ts}"      # ✓ Matches .js and .ts files
  - "packages/*/src/**/*.go" # ✓ Matches across package structure
```

**Not**:

```yaml
sources:
  - "src"                   # ✗ Not a glob pattern - won't match files
  - "*.py"                  # ✗ Only matches project root, not subdirectories
```

See [Configuration reference](../reference/file-formats.md#doc-manageryml) for details.

### Choose appropriate sync mode

- **`mode="check"`**: Analysis without side effects
  - Use after code changes to assess impact
  - Use in CI/CD for quality gates
  - Safe to run frequently

- **`mode="resync"`**: Analysis + baseline update
  - Use after updating documentation
  - Requires documentation to be in sync with code
  - Resets change detection baseline

### Enable root README tracking

To include root `README.md` in operations:

```yaml
include_root_readme: true
```

Useful when root README serves as landing page or contains important documentation.

### Validate early and often

Run validation before committing:
- Catches broken links immediately
- Prevents accumulation of issues
- Maintains documentation quality

### Use semantic change detection selectively

Enable `include_semantic=true` when:
- Making API changes
- Refactoring code structure
- Need detailed change analysis

Skip it when:
- Only docs changed
- Performance matters (semantic detection is slower)
- Running frequently in automation

---

## See also

- [Claude Code Plugin](claude-code-plugin.md) - Agents and commands for interactive use
- [Tools reference](../reference/tools.md) - Detailed tool documentation
- [File formats](../reference/file-formats.md) - Configuration and baseline files
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Platform support](platforms.md) - Platform-specific guidance
