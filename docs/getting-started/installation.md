# Installation

## Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`
- Git (for version control features)
- TreeSitter language pack (installed automatically with dependencies)

## Installation methods

### Method 1: Install from PyPI (recommended)

```bash
pip install doc-manager-mcp
```

### Method 2: Install from source

```bash
git clone https://github.com/yourusername/doc-manager
cd doc-manager
pip install -e .
```

### Method 3: Install with uv

```bash
uv pip install doc-manager-mcp
```

## MCP server configuration

To use Documentation Manager as an MCP server, add it to your MCP settings file:

```json
{
  "mcpServers": {
    "doc-manager": {
      "command": "uvx",
      "args": ["--from", "doc-manager-mcp", "doc-manager"]
    }
  }
}
```

Or for local development:

```json
{
  "mcpServers": {
    "doc-manager": {
      "command": "uvx",
      "args": ["--from", "/path/to/doc-manager", "doc-manager"]
    }
  }
}
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
