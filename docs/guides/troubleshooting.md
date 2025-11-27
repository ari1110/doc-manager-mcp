# Troubleshooting

Common issues and solutions for doc-manager.

## Installation issues

### TreeSitter not available

**Symptom**: "TreeSitter not available" warning message

**Cause**: TreeSitter language pack not installed.

**Solution**:

```bash
pip install tree-sitter tree-sitter-language-pack
```

### Permission errors on Windows

**Symptom**: Permission denied errors during installation

**Cause**: Installation requires elevated permissions.

**Solution**:

Try running your terminal as administrator or use:

```bash
pip install --user doc-manager-mcp
```

### Import errors

**Symptom**: `ImportError` or `ModuleNotFoundError` when running tools

**Cause**: Python version incompatibility.

**Solution**:

Ensure your Python version is 3.10 or higher:

```bash
python --version
```

If below 3.10, upgrade Python before installing doc-manager.

---

## Configuration issues

### Symbols not being extracted

**Symptom**: `symbol-baseline.json` is empty or has very few symbols

**Cause**: Source patterns in `.doc-manager.yml` don't match your files or aren't glob patterns.

**Solution**:

1. Verify `sources` uses **glob patterns**, not directory names:

```yaml
sources:
  - "src/**/*.py"           # ✓ Correct - glob pattern
  - "lib/**/*.{js,ts}"      # ✓ Correct - multiple extensions
```

Not:

```yaml
sources:
  - "src"                   # ✗ Wrong - not a glob pattern
  - "*.py"                  # ✗ Wrong - only matches root directory
```

2. Check patterns match your files: test with `ls src/**/*.py`
3. Ensure no exclude patterns are blocking your sources
4. Regenerate baselines after fixing patterns

### Too many files tracked

**Symptom**: `repo-baseline.json` tracks thousands of unwanted files

**Cause**: Exclude patterns not configured properly.

**Solution**:

1. Add specific exclude patterns in `.doc-manager.yml`:

```yaml
exclude:
  - "node_modules/**"
  - "vendor/**"
  - "**/__pycache__/**"
  - ".venv/**"
  - "dist/**"
```

2. Make source patterns more restrictive
3. Check `repo-baseline.json` to see what's being tracked after changes

### Platform not detected

**Symptom**: `docmgr_detect_platform` returns `"unknown"` or incorrect platform

**Cause**: No recognizable platform config files, or config files in non-standard location.

**Solution**:

1. Check for platform config files in project root or docs directory:
   - MkDocs: `mkdocs.yml` or `mkdocs.yaml`
   - Sphinx: `docs/conf.py`
   - Hugo: `config.toml` or `hugo.toml`
   - Docusaurus: `docusaurus.config.js`

2. If using a platform but config is missing, manually specify in `docmgr_init`:

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "existing",
    "platform": "mkdocs"  // Specify explicitly
  }
}
```

3. If no platform is in use, set to `"unknown"`:

```yaml
# .doc-manager.yml
platform: unknown
```

### Config file not found

**Symptom**: "Config file .doc-manager.yml not found" error

**Cause**: `docmgr_init` has not been run yet.

**Solution**:

Run initialization:

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "existing"
  }
}
```

This creates `.doc-manager.yml` and baseline files.

---

## Baseline issues

### Baseline files missing or corrupted

**Symptom**: Tools fail with "baseline not found" or "invalid baseline format"

**Causes**:
- Baseline files deleted
- File corruption
- Incomplete initialization

**Solution**:

Regenerate all baselines:

```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

If that fails, reinitialize (will overwrite config):

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "existing"
  }
}
```

### Dependencies file shows no mappings

**Symptom**: `.doc-manager/dependencies.json` has empty `doc_to_code` or `code_to_doc`

**Causes**:
- Documentation doesn't reference code files
- Source patterns don't match files
- Documentation uses only external references

**Solution**:

1. Verify documentation contains code references (file paths, function names, class names)

2. Check source patterns match your code:

```yaml
sources:
  - "src/**/*.py"  # Adjust to match your project structure
```

3. Regenerate dependencies:

```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

4. If using mostly external references, this is expected behavior.

### Baseline out of sync with git

**Symptom**: Change detection shows false positives after git operations (merge, rebase, etc.)

**Cause**: Baselines reference old git commits or file states.

**Solution**:

Update baselines to current state:

```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Or use `docmgr_sync mode="resync"` to update atomically.

---

## Validation errors

### Code blocks missing language tags

**Symptom**: Validation reports "Code block missing language tag"

**Cause**: Code fence doesn't specify language:

````text
```
code here  ← Missing language tag!
```
````

**Solution**:

Add language identifier:

````markdown
```python
code here
```
````

Common language tags: `python`, `javascript`, `bash`, `yaml`, `json`, `typescript`, `go`, `rust`

### Broken internal links

**Symptom**: "Link target does not exist: path/to/file.md"

**Causes**:
- Typo in link path
- File moved or renamed
- Incorrect relative path

**Solution**:

1. Check link path in reported file and line

2. Verify target file exists relative to source file

3. Fix link path:

```markdown
<!-- Before -->
[Guide](../guides/nonexistent.md)

<!-- After -->
[Guide](../guides/workflows.md)
```

4. For cross-directory links, verify `../` navigation is correct

### Missing alt text on images

**Symptom**: "Image missing alt text: images/screenshot.png"

**Cause**: Image reference lacks alt text:

```markdown
![](images/screenshot.png)
```

**Solution**:

Add descriptive alt text:

```markdown
![Screenshot of the dashboard showing metrics](images/screenshot.png)
```

Alt text improves accessibility and SEO.

### Validation shows outdated symbol references

**Symptom**: "Symbol 'old_function' not found in codebase" (when `validate_symbols=true`)

**Cause**: Documentation references symbols that have been renamed or removed.

**Solution**:

1. Update documentation to reference current symbols

2. If symbol was renamed, update references:

```markdown
<!-- Before -->
Use `old_function()` to process data.

<!-- After -->
Use `process_data()` to process data.
```

3. If symbol was removed, update or remove documentation section

4. Regenerate baselines after fixing:

```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

---

## Quality assessment issues

### Low API coverage

**Symptom**: Quality assessment shows `api_coverage: 5%` or similar low percentage

**Cause**: Most public symbols are undocumented.

**Solution**:

1. Identify undocumented symbols from quality assessment findings

2. Add documentation for public APIs, classes, and functions

3. Focus on:
   - Public APIs (prioritize over internal functions)
   - User-facing functionality
   - Complex or non-obvious behavior

4. Run quality assessment again to track progress

**Note**: 100% coverage is not always necessary. Target coverage based on project needs (20-40% for internal tools, 80%+ for public libraries).

### Duplicate content detected

**Symptom**: Quality assessment reports duplicate topics across multiple files

**Cause**: Same information documented in multiple places.

**Solution**:

1. Review reported duplicate sections

2. Consolidate into single source of truth:
   - Keep most detailed version
   - Remove or replace duplicates with cross-references

3. Add links instead of duplication:

```markdown
<!-- Instead of duplicating installation steps -->
See [Installation Guide](installation.md) for setup instructions.
```

4. Re-run quality assessment to confirm improvement

### Inconsistent heading case

**Symptom**: Quality assessment reports mixed heading styles (Title Case, sentence case, etc.)

**Cause**: No consistent heading convention.

**Solution**:

1. Choose a heading style (sentence case recommended for technical docs)

2. Update `.doc-manager/memory/doc-conventions.yml`:

```yaml
style:
  headings:
    case: sentence_case  # or title_case
    consistency_required: true
```

3. Fix headings throughout documentation:

```markdown
<!-- Before (mixed) -->
# Getting Started
## Configure the system
### Important Notes

<!-- After (consistent sentence case) -->
# Getting started
## Configure the system
### Important notes
```

4. Validation will now enforce chosen style

---

## Migration issues

### Git history not preserved

**Symptom**: After `docmgr_migrate` with `preserve_history=true`, git log doesn't show file history

**Cause**: Git working directory had uncommitted changes, or git operations failed.

**Solution**:

1. Ensure clean working directory before migration:

```bash
git status  # Should show "nothing to commit, working tree clean"
```

2. Commit or stash changes:

```bash
git add .
git commit -m "Commit before doc migration"
# Or: git stash
```

3. Run migration again

4. Verify history preserved:

```bash
git log --follow docs/moved-file.md
```

### Links broken after migration

**Symptom**: Validation shows broken links after running `docmgr_migrate`

**Cause**: Internal links not rewritten to match new structure.

**Solution**:

1. Run migration with `rewrite_links=true`:

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "project_path": "/path/to/project",
    "source_path": "old-docs",
    "target_path": "docs",
    "rewrite_links": true  // Enable link rewriting
  }
}
```

2. For complex migrations, manually review and fix links

3. Run validation to confirm all links fixed:

```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "project_path": "/path/to/project",
    "check_links": true
  }
}
```

### Migration fails with "target path already exists"

**Symptom**: `docmgr_migrate` errors because target directory exists

**Cause**: Target path conflicts with existing directory.

**Solutions**:

**Option 1**: Migrate to different target path

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "target_path": "documentation"  // Use different name
  }
}
```

**Option 2**: Manually backup and remove existing target:

```bash
mv docs docs-backup
# Then run migration
```

**Option 3**: Use `dry_run=true` first to review:

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "dry_run": true
  }
}
```

---

## Performance issues

### Slow change detection

**Symptom**: `docmgr_detect_changes` takes long time (>30 seconds for medium projects)

**Cause**: `include_semantic=true` enables expensive TreeSitter AST parsing.

**Solutions**:

1. Disable semantic analysis if not needed:

```json
{
  "tool": "docmgr_detect_changes",
  "arguments": {
    "include_semantic": false  // Faster, checksum-only
  }
}
```

2. Exclude large directories from tracking:

```yaml
exclude:
  - "node_modules/**"
  - "vendor/**"
  - "dist/**"
  - ".venv/**"
```

3. Use `mode="git_diff"` for faster comparison:

```json
{
  "tool": "docmgr_detect_changes",
  "arguments": {
    "mode": "git_diff",
    "since_commit": "HEAD~1"
  }
}
```

### Validation timeout or memory issues

**Symptom**: `docmgr_validate_docs` runs out of memory or times out

**Cause**: Too many files, or deep syntax validation enabled.

**Solutions**:

1. Disable expensive checks:

```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "validate_code_syntax": false,  // Disable TreeSitter validation
    "validate_symbols": false       // Disable symbol checking
  }
}
```

2. Validate specific subdirectory:

```json
{
  "tool": "docmgr_validate_docs",
  "arguments": {
    "docs_path": "docs/guides"  // Validate subset
  }
}
```

3. Exclude large or generated files:

```yaml
exclude:
  - "docs/api-reference/**"  # Exclude auto-generated docs
  - "**/*.tmp"
```

---

## Git integration issues

### "Not a git repository" error

**Symptom**: Operations fail with git-related errors

**Cause**: Project directory is not a git repository.

**Solution**:

Initialize git repository:

```bash
cd /path/to/project
git init
git add .
git commit -m "Initial commit"
```

Or, if git integration not needed, some tools will work without it (but `preserve_history` in migration won't work).

### Baseline contains wrong git commit

**Symptom**: `repo-baseline.json` references outdated commit hash

**Cause**: Baseline not updated after git operations.

**Solution**:

Update baseline to current commit:

```json
{
  "tool": "docmgr_update_baseline",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

Baseline will capture current `HEAD` commit.

---

## MCP server issues

### Tool not found or unavailable

**Symptom**: MCP client reports tool doesn't exist

**Cause**: Server not running, or client not connected properly.

**Solution**:

1. Verify MCP server is running

2. Check client configuration points to correct server

3. Restart MCP server if needed

4. Confirm tool name is correct (e.g., `docmgr_init`, not `init`)

### Tool returns unexpected format

**Symptom**: Tool output doesn't match expected structure

**Cause**: Version mismatch between server and client expectations.

**Solution**:

1. Check doc-manager version:

```bash
pip show doc-manager-mcp
```

2. Update to latest version:

```bash
pip install --upgrade doc-manager-mcp
```

3. Restart MCP server after updating

---

## Getting help

If you encounter issues not covered here:

1. **Check the logs**: Look for error messages with details

2. **Verify configuration**: Run through [configuration checklist](../reference/file-formats.md)

3. **Try dry run**: For state-changing operations, use `dry_run=true` first

4. **Reset baselines**: Many issues resolve with `docmgr_update_baseline`

5. **Report bugs**: Open an issue with:
   - Error message
   - Tool used and arguments
   - `.doc-manager.yml` contents (redact sensitive paths)
   - Project structure overview

## See also

- [Workflows](workflows.md) - Step-by-step workflow guides
- [Tools reference](../reference/tools.md) - Detailed tool documentation
- [File formats](../reference/file-formats.md) - Configuration file details
- [Platform support](platforms.md) - Platform-specific guidance
