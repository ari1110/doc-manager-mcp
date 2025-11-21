# docmgr_validate_docs

Validate documentation for broken links, missing assets, code snippet syntax, and convention compliance.

## Purpose

Performs comprehensive validation checks on documentation files to catch broken links, missing assets, syntax errors in code blocks, and violations of documentation conventions.

## When to use

- Before releases to ensure documentation quality
- After major documentation updates
- As part of CI/CD pipeline to catch issues early
- When fixing validation issues (run to verify fixes)
- After migrating or restructuring documentation

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |
| `docs_path` | string | No | `null` | Override docs path from config |
| `check_links` | bool | No | `true` | Validate internal links point to existing files |
| `check_assets` | bool | No | `true` | Verify images/assets exist and have alt text |
| `check_snippets` | bool | No | `true` | Validate code block syntax |
| `validate_code_syntax` | bool | No | `false` | Deep syntax validation with TreeSitter (slower) |
| `validate_symbols` | bool | No | `false` | Check documented symbols exist in codebase |

## Output

```json
{
  "status": "issues_found",
  "total_issues": 12,
  "issues_by_severity": {
    "error": 3,
    "warning": 7,
    "info": 2
  },
  "issues": [
    {
      "file": "docs/api.md",
      "line": 42,
      "type": "broken_link",
      "severity": "error",
      "message": "Link target does not exist: guides/nonexistent.md"
    },
    {
      "file": "docs/tutorial.md",
      "line": 15,
      "type": "missing_alt_text",
      "severity": "warning",
      "message": "Image missing alt text: images/screenshot.png"
    },
    {
      "file": "docs/reference.md",
      "line": 88,
      "type": "code_syntax_error",
      "severity": "error",
      "message": "Python code block has syntax error: unexpected EOF"
    }
  ]
}
```

## Examples

### Basic validation

```python
await mcp.call_tool("docmgr_validate_docs", {
  "project_path": "/path/to/project"
})
```

### Skip asset checks

```python
await mcp.call_tool("docmgr_validate_docs", {
  "project_path": "/path/to/project",
  "check_links": true,
  "check_assets": false,
  "check_snippets": true
})
```

### Deep validation with symbol checking

```python
await mcp.call_tool("docmgr_validate_docs", {
  "project_path": "/path/to/project",
  "validate_code_syntax": true,
  "validate_symbols": true
})
```

## Validation checks

### Link validation (`check_links=true`)

- Internal links point to existing files
- Anchor links reference existing headings
- Relative paths resolve correctly
- No broken cross-references

### Asset validation (`check_assets=true`)

- Referenced images/media files exist
- Images have alt text (accessibility)
- Asset paths are valid
- No orphaned assets

### Code snippet validation (`check_snippets=true`)

- Code blocks have language tags
- Basic syntax checks for common languages
- Proper code block formatting
- No unclosed code fences

### Deep code validation (`validate_code_syntax=true`)

- Uses TreeSitter for AST-based syntax validation
- Detects actual syntax errors in code examples
- Language-specific validation rules
- **Note**: Slower, only enable when needed

### Symbol validation (`validate_symbols=true`)

- Checks if documented functions/classes exist in codebase
- Validates API references are accurate
- Detects outdated symbol references
- Requires symbol baseline to exist

## Issue severities

- **error**: Critical issues that should be fixed (broken links, syntax errors)
- **warning**: Important issues that affect quality (missing alt text, convention violations)
- **info**: Minor suggestions for improvement

## Notes

- **Read-only**: Only analyzes documentation, makes no changes
- **Performance**: Deep validation (`validate_code_syntax`, `validate_symbols`) is slower
- **Convention compliance**: Uses rules from `.doc-manager/memory/doc-conventions.yml`
- **Root README**: Includes root README.md if `include_root_readme: true` in config
- **Prerequisites**: Requires `.doc-manager.yml` to exist

## Typical workflow

```text
1. Run docmgr_validate_docs to find issues
2. Fix reported errors and warnings
3. Re-run validation to confirm fixes
4. Repeat until validation passes cleanly
```

## See also

- [docmgr_assess_quality](docmgr_assess_quality.md) - Quality assessment beyond validation
- [Documentation conventions](../file-formats.md#doc-managermemorydoc-conventionsyml)
- [Troubleshooting guide](../../guides/troubleshooting.md)
