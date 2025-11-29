# Claude Code Plugin

The Claude Code plugin wraps the doc-manager MCP server with specialized agents, quick commands, and contextual awareness - making documentation management feel natural within your coding workflow.

## What the plugin adds

The raw MCP server gives you 8 tools for documentation management. The plugin layers on top:

| Layer | What it provides |
|-------|-----------------|
| **Agents** | Expert associates who use the tools, analyze results, and act on them |
| **Commands** | Quick slash commands for common workflows |
| **Skill** | Contextual awareness that suggests documentation tasks at the right moments |

## Two agents, two roles

The plugin uses a division of labor:

### Doc-expert (documentation expert)

The expert associate for documentation. Uses the MCP tools to analyze and assess documentation state, then acts on results - asking clear questions when needed or providing direction on next steps. Delegates content fixes to doc-writer.

**Use for:**
- Setting up documentation management (`"Set up docs for this project"`)
- Quality audits (`"Check documentation quality"`)
- Syncing after code changes (`"Sync docs with recent changes"`)
- Migrations (`"Move docs from docs/ to documentation/"`)

### Doc-writer (content specialist)

Focuses purely on writing and updating documentation content. Has limited tool access (just change detection and validation).

**Use for:**
- Creating new docs (`"Document the new API endpoint"`)
- Updating existing guides (`"Update installation guide with Docker setup"`)

The agents coordinate automatically - doc-expert delegates content work to doc-writer, then validates the results.

## Quick commands

Three slash commands for fast access:

| Command | What it does |
|---------|-------------|
| `/doc-status` | Quick health check - are docs in sync with code? |
| `/doc-sync` | Full sync workflow - detect, update, validate, baseline |
| `/doc-quality` | Quality assessment against 7 criteria |

## Contextual awareness

The plugin's skill activates when you mention:

- **Release/deploy/merge** - Offers documentation health checks
- **Documentation terms** - Presents options for what you might need
- **Code changes** - Suggests syncing docs

It suggests, it doesn't demand. You control when heavy workflows run.

## Installation

```bash
/plugin marketplace add ari1110/doc-manager-mcp
/plugin install doc-management@doc-manager-suite
```

The plugin automatically configures the doc-manager MCP server.

## Example workflow

Here's what using the plugin feels like:

```text
You: "I've refactored the authentication module"

Claude: "Would you like me to sync the documentation?
I can detect what changed and update affected docs.
Use /doc-sync or say 'sync docs' to proceed."

You: "sync docs"

Claude: [Invokes doc-expert]
- Detected 8 changed files in src/auth/
- 3 documentation files affected: api.md, guides/auth.md, security.md
- [Delegates to doc-writer for content updates]
- [Validates and assesses quality]
- All done. Documentation updated and baseline refreshed.
```

## When to use raw tools vs. plugin

| Scenario | Use |
|----------|-----|
| Complex multi-step workflows | Plugin (agents handle coordination) |
| Quick one-off checks | Plugin commands (`/doc-status`) |
| Scripted CI/CD integration | Raw MCP tools |
| Fine-grained control | Raw MCP tools |

The plugin is for interactive work. The raw tools are for automation and integration.
