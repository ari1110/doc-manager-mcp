# docmgr_detect_platform

Auto-detect documentation platform or recommend one.

## Purpose

Analyzes project structure to identify which documentation platform is in use (MkDocs, Sphinx, Hugo, etc.) or recommends a platform based on project language and characteristics.

## When to use

- Before running `docmgr_init` when unsure which platform is in use
- When documenting a new project and need platform recommendations
- To verify current documentation platform detection
- As part of migration planning

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |

## Output

### When platform detected

```json
{
  "platform": "mkdocs",
  "confidence": "high",
  "evidence": [
    "Found mkdocs.yml config file",
    "Found docs/ directory with index.md"
  ]
}
```

### When platform not detected

```json
{
  "platform": "unknown",
  "recommendations": [
    {
      "platform": "sphinx",
      "reason": "Python project with extensive API documentation needs",
      "confidence": "medium"
    },
    {
      "platform": "mkdocs",
      "reason": "Simple setup, good for quick documentation",
      "confidence": "low"
    }
  ],
  "project_language": "Python"
}
```

## Examples

### Detect platform before init

```python
result = await mcp.call_tool("docmgr_detect_platform", {
  "project_path": "/path/to/project"
})

# Use detected platform for init
await mcp.call_tool("docmgr_init", {
  "project_path": "/path/to/project",
  "platform": result["platform"]
})
```

### Get recommendations for new project

```python
await mcp.call_tool("docmgr_detect_platform", {
  "project_path": "/path/to/new-project"
})
```

## Supported platforms

Platform detection looks for these config files:

| Platform | Config Files | Description |
|----------|--------------|-------------|
| **mkdocs** | `mkdocs.yml`, `mkdocs.yaml` | Popular Python-based static site generator |
| **sphinx** | `conf.py` (in docs/) | Python documentation generator with rich features |
| **hugo** | `config.toml`, `hugo.toml`, `config.yaml` | Fast Go-based static site generator |
| **docusaurus** | `docusaurus.config.js`, `docusaurus.config.ts` | React-based documentation framework |
| **vitepress** | `.vitepress/config.js`, `.vitepress/config.ts` | Vue-powered static site generator |
| **jekyll** | `_config.yml` | Ruby-based static site generator |
| **gitbook** | `.gitbook.yaml`, `book.json` | Modern documentation platform |

## Notes

- **Read-only**: Only analyzes project files, makes no changes
- **Detection order**: Checks for platform-specific config files in project root and docs directory
- **Confidence levels**:
  - `high`: Config file found with matching directory structure
  - `medium`: Config file found but structure unclear
  - `low`: No config found, recommending based on project type
- **Recommendations**: Based on project language, size, and common patterns
- **Fallback**: Returns `"unknown"` if no platform detected and no strong recommendation

## Typical workflow

```
1. Run docmgr_detect_platform to identify platform
2. Review detected platform or recommendations
3. Use platform value for docmgr_init
```

## See also

- [docmgr_init](docmgr_init.md) - Initialize with detected platform
- [Platform support guide](../../guides/platforms.md) - Platform-specific documentation
