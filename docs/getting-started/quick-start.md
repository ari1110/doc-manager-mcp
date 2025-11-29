# Quick start

Get up and running with Documentation Manager MCP server in 5 minutes.

> **Using Claude Code?** Consider the [plugin](../guides/claude-code-plugin.md) which adds agents and quick commands for an interactive workflow.

## Step 1: Add to MCP client

Add to your MCP settings file (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "doc-manager": {
      "command": "uvx",
      "args": ["doc-manager-mcp"]
    }
  }
}
```

Restart your MCP client (e.g., Claude Desktop) to load the server.

## Step 2: Initialize for your project

Choose the workflow that matches your situation:

### For projects with existing documentation

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/your/project",
    "mode": "existing",
    "docs_path": "docs"
  }
}
```

This creates `.doc-manager.yml` configuration and baselines without modifying existing docs.

### For projects without documentation

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/your/project",
    "mode": "bootstrap",
    "docs_path": "docs"
  }
}
```

This generates a complete documentation structure with templates.

## Step 3: Configure source tracking

Edit `.doc-manager.yml` to specify which source files to track using **glob patterns**:

```yaml
sources:
  - "src/**/*.py"      # Python files
  - "lib/**/*.js"      # JavaScript files
exclude:
  - "tests/**"         # Exclude tests
  - "**/__pycache__/**"
```

**Important:** Use glob patterns (e.g., `"src/**/*.py"`), not plain directory names like `"src"`.

## Step 4: Sync and validate

Run a sync check to see the current state:

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/your/project",
    "mode": "check"
  }
}
```

This performs:
- Change detection
- Documentation validation
- Quality assessment
- Recommendations for updates

## Step 5: Update baselines after doc changes

After updating your documentation to reflect code changes:

```json
{
  "tool": "docmgr_sync",
  "arguments": {
    "project_path": "/path/to/your/project",
    "mode": "resync"
  }
}
```

This updates all baselines atomically to match the current codebase.

## Next steps

- [Claude Code Plugin](../guides/claude-code-plugin.md) - Agents and commands for interactive use
- [Workflows Guide](../guides/workflows.md) - Learn about common workflows
- [Configuration Reference](../reference/configuration.md) - Detailed config options
- [Tools Reference](../reference/tools.md) - Complete API documentation
