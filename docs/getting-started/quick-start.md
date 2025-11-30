# Quick start

Get started with doc-manager in your project.

## With Claude Code plugin

If you're using the [Claude Code plugin](../guides/claude-code-plugin.md), the workflow is conversational:

```text
You: "Set up documentation management for this project"
Claude: [Invokes @doc-expert to detect platform and initialize]

You: "I changed some code, sync the docs"
Claude: [Detects changes, shows what needs updating]

You: "/doc-sync"
Claude: [Runs full sync workflow]
```

**Common commands:**
- `/doc-status` - Quick health check
- `/doc-sync` - Full sync (detect → validate → update baselines)
- `/doc-quality` - Quality assessment

See the [plugin guide](../guides/claude-code-plugin.md) for details.

---

## With standalone MCP server

If you're using Claude Desktop or another MCP client, ask your AI assistant in natural language:

**Setup:**
> "Initialize documentation management for this project"

Your AI will use `docmgr_detect_platform` and `docmgr_init` to set things up.

**After making code changes:**
> "Check if my documentation needs updating"

Your AI will use `docmgr_detect_changes` to analyze what changed.

**Before a release:**
> "Validate my documentation and check quality"

Your AI will use `docmgr_validate_docs` and `docmgr_assess_quality` to audit your docs.

---

## Configuration

After initialization, edit `.doc-manager.yml` to configure source tracking:

```yaml
sources:
  - "src/**/*.py"      # Python files
  - "lib/**/*.js"      # JavaScript files
exclude:
  - "tests/**"         # Exclude tests
  - "**/__pycache__/**"
```

**Important:** Use glob patterns (e.g., `"src/**/*.py"`), not plain directory names like `"src"`.

---

## Understanding the workflow

Doc-manager tracks your codebase with three baseline files in `.doc-manager/memory/`:

1. **repo-baseline.json** - File checksums for change detection
2. **symbol-baseline.json** - Code symbols (functions, classes)
3. **dependencies.json** - Code-to-docs mappings

**Typical workflow:**

1. **Initialize** - Create baselines for your project
2. **Make code changes** - Modify your source code
3. **Detect changes** - See what code changed and which docs are affected
4. **Update docs** - Fix the documentation
5. **Resync** - Update baselines to match current state

The cycle repeats as you develop.

---

## Next steps

- [Workflows Guide](../guides/workflows.md) - Common workflows and patterns
- [Configuration Reference](../reference/configuration.md) - Detailed config options
- [Tools Reference](../reference/tools.md) - Complete API documentation
