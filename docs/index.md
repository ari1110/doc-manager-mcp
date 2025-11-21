# Documentation Manager MCP Server

## Overview

Documentation Manager is an MCP (Model Context Protocol) server that automates documentation lifecycle management for software projects. It helps you create, maintain, validate, and keep documentation synchronized with your codebase using intelligent change detection and quality assessment.

## Key features

- **Automated documentation bootstrapping** - Generate documentation structure from scratch
- **Intelligent change detection** - Track code changes using checksums and semantic analysis
- **Quality assessment** - Evaluate docs against 7 criteria (relevance, accuracy, purposefulness, uniqueness, consistency, clarity, structure)
- **Link and asset validation** - Catch broken links, missing assets, and invalid code snippets
- **Convention enforcement** - Apply documentation standards (heading case, code block languages, etc.)
- **Dependency tracking** - Automatic code-to-docs mapping with TreeSitter symbol extraction
- **Platform support** - Works with MkDocs, Sphinx, Hugo, Docusaurus, and more

## Architecture

The server provides 8 tools organized into 4 tiers:

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

## Quick example

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "project_path": "/path/to/project",
    "mode": "bootstrap",
    "docs_path": "docs"
  }
}
```

This creates a complete documentation structure with configuration, baselines, and templates.

## Documentation sections

### Getting started
Learn how to install and start using Documentation Manager.

### Guides
Step-by-step tutorials for common tasks like syncing docs with code changes.

### Reference
Detailed technical reference for all tools, configuration options, and conventions.
