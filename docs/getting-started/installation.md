# Installation

Documentation Manager is an MCP (Model Context Protocol) server that integrates with Claude Desktop and other MCP clients to automate documentation lifecycle management.

## Prerequisites

- Python 3.10 or higher
- An MCP client (like Claude Desktop)
- Git (optional, for version control features)

## Quick setup

Add Documentation Manager to your MCP settings file (e.g., `claude_desktop_config.json`):

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

That's it! The MCP client will automatically download and run the server when needed.

## Claude Code plugin

For Claude Code users, the plugin adds specialized agents, quick commands, and contextual awareness:

```bash
# Add the MCP server (project-scoped)
claude mcp add doc-manager-mcp --project -- uvx doc-manager-mcp

# Install the plugin (project-scoped)
claude plugin install doc-management --project
```

The `--project` flag keeps the plugin scoped to projects that need it. See the [Claude Code Plugin guide](../guides/claude-code-plugin.md) for what the plugin enables.

## Alternative installation methods

### Local development

For contributing or testing local changes:

```json
{
  "mcpServers": {
    "doc-manager": {
      "command": "uvx",
      "args": ["--from", "/path/to/doc-manager-mcp", "doc-manager-mcp"]
    }
  }
}
```

### Standalone installation (advanced)

If you need to install the package directly (not common for MCP usage):

```bash
# With pip
pip install doc-manager-mcp

# From source
git clone https://github.com/ari1110/doc-manager-mcp
cd doc-manager-mcp
pip install -e .
```

## Verification

Verify the installation by checking the tools are available in your MCP client. You should see 8 tools:

- `docmgr_init`
- `docmgr_detect_changes`
- `docmgr_detect_platform`
- `docmgr_validate_docs`
- `docmgr_assess_quality`
- `docmgr_update_baseline`
- `docmgr_sync`
- `docmgr_migrate`

## Troubleshooting

Having installation issues? See the [Troubleshooting guide](../guides/troubleshooting.md#installation-issues) for solutions to:

- TreeSitter not available
- Permission errors on Windows
- Import errors
- Python version compatibility

For other issues, check the [complete troubleshooting guide](../guides/troubleshooting.md).
