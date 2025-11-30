# API reference

Python API reference for the doc-manager MCP server implementation.

## Overview

This section documents the Python Pydantic models and enumerations used by the doc-manager MCP server. These are the data structures used for tool input validation and output serialization.

## Sections

### [Models reference](./models.md)

Complete reference for all Pydantic model classes:

- **Input Models** - Validated request parameters for all tools
  - `DocmgrInitInput` - Initialization parameters
  - `DocmgrDetectChangesInput` - Change detection parameters
  - `DocmgrUpdateBaselineInput` - Baseline update parameters
  - `ValidateDocsInput` - Documentation validation parameters
  - `AssessQualityInput` - Quality assessment parameters
  - `MigrateInput` - Documentation migration parameters
  - `SyncInput` - Synchronization parameters
  - `DetectPlatformInput` - Platform detection parameters

- **Convention Models** - Documentation standards configuration
  - `DocumentationConventions` - Complete conventions schema
  - `StyleConventions` - Style rules (headings, code, voice)
  - `StructureConventions` - Structure rules (intro, TOC, hierarchy)
  - `QualityConventions` - Quality rules (sentences, paragraphs, links, images, code)
  - `TerminologyConventions` - Terminology rules (preferred terms, words to avoid)

- **Output Models** - Structured response data
  - `MapChangesOutput` - Change detection results

Each model includes:
- Field definitions with types and descriptions
- Default values
- Validation rules
- Usage examples

### [Enums reference](./enums.md)

Complete reference for all enumeration types:

- **DocumentationPlatform** - Supported documentation platforms
  - Values: `hugo`, `docusaurus`, `mkdocs`, `sphinx`, `vitepress`, `jekyll`, `gitbook`, `unknown`
  - When to use each platform
  - Platform detection behavior

- **QualityCriterion** - Documentation quality assessment criteria
  - Values: `relevance`, `accuracy`, `purposefulness`, `uniqueness`, `consistency`, `clarity`, `structure`
  - What each criterion measures
  - Typical assessment order
  - Scoring guidance

- **ChangeDetectionMode** - Change detection methods
  - Values: `checksum`, `git_diff`
  - When to use each mode
  - Mode-specific requirements and limitations

Each enum includes:
- All values with descriptions
- When to use each value
- Usage examples
- Common mistakes and how to avoid them

---

## Quick reference

### Input model fields by tool

**DocmgrInitInput** (docmgr_init):
```text
project_path (required), mode, platform, exclude_patterns, docs_path, sources, include_root_readme, use_gitignore
```

**DocmgrDetectChangesInput** (docmgr_detect_changes):
```text
project_path (required), since_commit, mode, include_semantic
```

**ValidateDocsInput** (docmgr_validate_docs):
```text
project_path (required), docs_path, check_links, check_assets, check_snippets, validate_code_syntax, validate_symbols, include_root_readme, incremental
```

**AssessQualityInput** (docmgr_assess_quality):
```text
project_path (required), docs_path, criteria, include_root_readme
```

**DocmgrUpdateBaselineInput** (docmgr_update_baseline):
```text
project_path (required), docs_path
```

**MigrateInput** (docmgr_migrate):
```text
project_path (required), source_path (required), target_path, target_platform, preserve_history, rewrite_links, regenerate_toc, dry_run
```

**SyncInput** (docmgr_sync):
```text
project_path (required), mode, docs_path
```

**DetectPlatformInput** (docmgr_detect_platform):
```text
project_path (required)
```

### Common patterns

**Creating an input model**:
```python
from doc_manager_mcp.models import DocmgrInitInput
from doc_manager_mcp.constants import DocumentationPlatform

init = DocmgrInitInput(
    project_path="/path/to/project",
    mode="bootstrap",
    platform=DocumentationPlatform.MKDOCS
)
```

**Using enums**:
```python
from doc_manager_mcp.constants import DocumentationPlatform, ChangeDetectionMode

platform = DocumentationPlatform.MKDOCS  # Type-safe
mode = ChangeDetectionMode.CHECKSUM
```

**Handling validation errors**:
```python
from pydantic import ValidationError

try:
    model = DocmgrInitInput(project_path="/invalid/path")
except ValidationError as e:
    for error in e.errors():
        print(f"Field: {error['loc'][0]}, Error: {error['msg']}")
```

---

## Validation rules

### Path validation

All path fields enforce strict validation:

- **Absolute paths**: Must be absolute, not relative (e.g., `/home/user/project` or `C:\Users\user\project`)
- **Path existence**: Must exist on filesystem
- **Type validation**: Must be directories where applicable
- **Security**: No path traversal sequences (`..`) allowed

### Glob pattern validation

Pattern lists enforce limits to prevent ReDoS:

- **Pattern length**: Max 512 characters per pattern
- **List length**: Max 50 patterns per list
- **ReDoS prevention**: Rejects patterns with nested quantifiers like `(a+)+`
- **Validation examples**:
  - Valid: `src/**/*.py`, `**/*.md`, `tests/**`
  - Invalid: `**/**/*.py` (nested globstars), `(a+)+b` (nested quantifiers)

### Security

Input validation prevents common attack vectors:

- **Command injection**: Git commit hashes validated as hex-only (7-40 chars)
- **Path traversal**: `..' sequences rejected in all path fields
- **Extra fields**: Unknown fields rejected (API boundary protection)
- **Type coercion**: Strict type checking, no implicit conversions

---

## Integration examples

### With MCP server

```python
from doc_manager_mcp.models import DocmgrDetectChangesInput
from doc_manager_mcp.constants import ChangeDetectionMode

# Create input from client request
input_data = {
    "project_path": "/path/to/project",
    "mode": "checksum",
    "include_semantic": True
}

# Validate and create model
try:
    request = DocmgrDetectChangesInput(**input_data)
    # Pass to tool handler
    result = await tool_handler(request)
except ValidationError as e:
    # Return validation error response
    return {"status": "error", "details": e.errors()}
```

### With Claude Code plugin

```python
from doc_manager_mcp.models import AssessQualityInput
from doc_manager_mcp.constants import QualityCriterion

# Quality assessment with specific criteria
assessment = AssessQualityInput(
    project_path="/path/to/project",
    criteria=[
        QualityCriterion.CLARITY,
        QualityCriterion.ACCURACY
    ]
)
```

---

## See also

- [Tools Reference](../tools.md) - Tool descriptions and usage
- [Configuration Reference](../configuration.md) - .doc-manager.yml schema
- [File Formats Reference](../file-formats.md) - Baseline and state files
