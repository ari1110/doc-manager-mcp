# Documentation Manager

## Overview

Documentation Manager helps you automate documentation lifecycle management for software projects. Powered by an MCP (Model Context Protocol) server, it helps you create, maintain, validate, and keep documentation synchronized with your codebase using intelligent change detection and quality assessment.

## Get started

### Recommended: Claude Code Plugin

The **doc-management plugin** provides an interactive workflow with specialized agents and quick commands.

**Install:**
```bash
/plugin marketplace add ari1110/doc-manager-mcp
/plugin install doc-manager@doc-manager-suite
```

**What you get:**
- `@doc-expert` - Expert associate for documentation analysis and workflow orchestration
- `@doc-writer` - Content specialist for writing and updating docs
- `/doc-status`, `/doc-sync`, `/doc-quality` - Quick commands

See the [Claude Code Plugin guide](guides/claude-code-plugin.md) for details.

### Alternative: Standalone MCP Server

For Claude Desktop or other MCP clients, install the [MCP server directly](getting-started/installation.md#option-2-standalone-mcp-server).

## Key features

- **Automated documentation bootstrapping** - Generate documentation structure from scratch
- **Intelligent change detection** - Track code changes using checksums and semantic analysis
- **Quality assessment** - Evaluate docs against 7 criteria (relevance, accuracy, purposefulness, uniqueness, consistency, clarity, structure)
- **Link and asset validation** - Catch broken links, missing assets, and invalid code snippets
- **Convention enforcement** - Apply documentation standards (heading case, code block languages, etc.)
- **Dependency tracking** - Automatic code-to-docs mapping with TreeSitter symbol extraction
- **Platform support** - Works with MkDocs, Sphinx, Hugo, Docusaurus, and more

## How it works

The doc-manager MCP server provides 8 tools organized into 4 tiers:

### Tier 1: Setup & initialization
- **docmgr_init** - Initialize doc-manager for existing projects or bootstrap new documentation

### Tier 2: Analysis & read-only operations
- **docmgr_detect_changes** - Detect code changes without modifying baselines (pure read-only)
- **docmgr_detect_platform** - Identify or recommend documentation platforms
- **docmgr_validate_docs** - Check for broken links, missing assets, invalid code snippets
- **docmgr_assess_quality** - Evaluate documentation quality against 7 criteria

### Tier 3: State management
- **docmgr_update_baseline** - Atomically update all baselines (repo, symbols, dependencies)
- **docmgr_sync** - Orchestrate change detection, validation, quality assessment, and baseline updates

### Tier 4: Workflows & orchestration
- **docmgr_migrate** - Restructure or migrate documentation with git history preservation

## Documentation sections

### Getting started
Learn how to [install](getting-started/installation.md) and [get started](getting-started/quick-start.md) with Documentation Manager.

### Guides
Step-by-step tutorials for common tasks:
- [Claude Code Plugin](guides/claude-code-plugin.md) - Interactive documentation workflow
- [Workflows](guides/workflows.md) - Common patterns and workflows
- [Config Field Tracking](guides/config-tracking.md) - Track configuration changes
- [Platforms](guides/platforms.md) - Platform-specific configuration

### Reference
Detailed technical reference:
- [Tools Reference](reference/tools.md) - Complete API documentation
- [Configuration](reference/configuration.md) - Configuration options
- [File Formats](reference/file-formats.md) - Baseline file schemas
