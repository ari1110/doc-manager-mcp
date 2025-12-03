# File formats reference

This document describes all files that doc-manager creates and manages in your project.

## Overview

Doc-manager creates files in the `.doc-manager/` directory to track documentation state, code changes, and configuration:

| File | Purpose | Auto-generated | Safe to edit |
|------|---------|----------------|--------------|
| `.doc-manager.yml` | Configuration | No | **Yes** |
| `.doc-manager/memory/repo-baseline.json` | File checksums for change detection | Yes | No |
| `.doc-manager/memory/symbol-baseline.json` | Code symbols (TreeSitter index) | Yes | No |
| `.doc-manager/dependencies.json` | Code-to-docs mappings | Yes | No |
| `.doc-manager/memory/doc-conventions.yml` | Documentation standards | Partially | **Yes** |

---

## .doc-manager.yml

**Purpose**: Main configuration file for doc-manager behavior.

**Location**: Project root

**When created**: `docmgr_init` with `mode="existing"` or manually

**Format**: YAML

### Structure

```yaml
platform: mkdocs              # Doc platform: mkdocs, sphinx, hugo, etc.
docs_path: docs               # Path to documentation directory
include_root_readme: false    # Include root README.md in doc operations

# Source file patterns (glob syntax required)
sources:
  - "src/**/*.py"
  - "lib/**/*.js"

# Files/directories to exclude from tracking
exclude:
  - "tests/**"
  - "**/__pycache__/**"
  - "dist/**"

metadata:
  language: Python
  created: '2025-11-20T20:22:51.007874'
  version: 1.0.0
```

### Key fields

**`platform`** (string)
- Documentation platform in use
- Common values: `mkdocs`, `sphinx`, `hugo`, `docusaurus`, `vitepress`, `unknown`
- Used for platform-specific conventions

**`docs_path`** (string)
- Relative path from project root to docs directory
- Default: `docs`

**`include_root_readme`** (boolean)
- When `true`, includes root `README.md` in validation, quality assessment, and dependency tracking
- Default: `false` (backwards compatible)

**`sources`** (list of strings)
- **Important**: Must use glob patterns (e.g., `"src/**/*.py"`), not plain directory names like `"src"`
- Specifies which source files to track for doc dependencies
- Empty list means only docs are tracked

**`exclude`** (list of strings)
- Glob patterns for files to exclude from baseline tracking
- Prevents noise from build artifacts, caches, etc.

### Safe to edit

**Yes** - This file is meant to be edited by users. Update it to match your project structure and preferences.

---

## .doc-manager/memory/repo-baseline.json

**Purpose**: Stores checksums of all tracked files for change detection.

**When updated**:
- `docmgr_init` (initial creation)
- `docmgr_update_baseline` (manual update)
- `docmgr_sync` with `mode="resync"` (automatic update)

**Format**: JSON

### Structure

```json
{
  "repo_name": "my-project",
  "description": "Repository for my-project",
  "language": "Python",
  "docs_exist": true,
  "docs_path": "docs",
  "metadata": {
    "git_commit": "abc123...",
    "git_branch": "main"
  },
  "timestamp": "2025-11-20T20:32:31.658435",
  "version": "1.0.0",
  "file_count": 65,
  "files": {
    ".doc-manager.yml": "ee1d7e230335ab8a5ebe74e4823e8778...",
    "docs/index.md": "fe502ddc88208ee6ca2cd203793222400c...",
    "src/main.py": "807ba5baf5ad268e5e91bf33d3cb3a65bf...",
    "docs/images/logo.png": "3340908a47d2b3c6b36873052c604ef84e..."
  }
}
```

### Key sections

**`files`** (object)
- Maps file paths (relative to project root) to SHA-256 checksums
- Includes:
  - Source files matching `sources` glob patterns
  - All files in `docs_path`
  - Configuration files (`.doc-manager.yml`)
  - Asset files (images, PDFs, etc.)

**`metadata`** (object)
- Git commit hash and branch at baseline creation
- Used to identify baseline version

### How it's used

When you run `docmgr_detect_changes`, it compares current file checksums against this baseline to identify:
- Modified files (changed checksums)
- New files (not in baseline)
- Deleted files (in baseline but missing)

Changes are categorized as: `code`, `documentation`, `asset`, `config`, `dependency`, `test`, `infrastructure`, or `other`.

### Safe to edit

**No** - This file is auto-generated. Manual edits will be overwritten on next baseline update. If checksums are wrong, run `docmgr_update_baseline` to regenerate.

---

## .doc-manager/memory/symbol-baseline.json

**Purpose**: Stores TreeSitter index of code symbols (classes, functions, methods) for semantic change detection.

**When updated**: Same as repo-baseline.json

**Format**: JSON

### Structure

```json
{
  "generated_at": "2025-11-20T20:32:37.265434",
  "files_indexed": 45,
  "total_symbols": 234,
  "symbols_by_type": {
    "class": 23,
    "function": 156,
    "method": 55
  },
  "index": {
    "MyClass": [
      {
        "name": "MyClass",
        "type": "class",
        "file": "src/models.py",
        "line": 42,
        "public": true
      }
    ],
    "process_data": [
      {
        "name": "process_data",
        "type": "function",
        "file": "src/utils.py",
        "line": 15,
        "public": true
      }
    ]
  }
}
```

### Key sections

**`index`** (object)
- Maps symbol names to their locations and metadata
- Extracted using TreeSitter AST parsing
- Only includes files matching `sources` patterns

**Supported languages**:
- Python, JavaScript, TypeScript, Go, Rust, Java, C, C++

### How it's used

- **Semantic change detection**: When `docmgr_detect_changes` is run with `include_semantic=true`, it can detect if a function/class was modified even if docs reference it
- **Symbol validation**: `docmgr_validate_docs` with `validate_symbols=true` checks if documented symbols still exist in code

### Troubleshooting

**Empty `index`**: See [Troubleshooting guide](../guides/troubleshooting.md#symbols-not-being-extracted) if symbol baseline is empty.

### Safe to edit

**No** - Auto-generated. Run `docmgr_update_baseline` to regenerate if needed.

---

## .doc-manager/dependencies.json

**Purpose**: Tracks relationships between documentation files and source code/assets.

**When updated**:
- `docmgr_init` (initial creation)
- `docmgr_update_baseline` (rebuilds mappings)
- `docmgr_sync` with `mode="resync"`

**Format**: JSON

### Structure

```json
{
  "generated_at": "2025-11-20T22:07:44.563480",
  "doc_to_code": {
    "guides/api.md": [
      "src/api/endpoints.py",
      "src/api/models.py"
    ]
  },
  "code_to_doc": {
    "src/api/endpoints.py": [
      "guides/api.md",
      "reference/api-reference.md"
    ]
  },
  "asset_to_docs": {
    "docs/images/architecture.png": [
      "guides/architecture.md"
    ]
  },
  "unmatched_references": {
    "some_function": [
      "guides/api.md"
    ]
  },
  "reference_to_doc": {
    "MyClass": [
      "guides/api.md",
      "reference/classes.md"
    ]
  },
  "all_references": {
    "file_path": [...],
    "function": [...],
    "class": [...],
    "command": [...],
    "config_key": [...]
  }
}
```

### Key sections

**`doc_to_code`** (object)
- Maps documentation files to source files they reference
- Built by scanning markdown for code references (inline code, file paths, symbols)

**`code_to_doc`** (object)
- Reverse mapping: source files → docs that reference them
- Useful for finding which docs need updating when code changes

**`asset_to_docs`** (object, optional)
- Maps asset files (images, PDFs) to docs that reference them
- Only present if assets are found
- Helps track which docs break if an asset is moved/deleted

**`unmatched_references`** (object)
- Code references in docs that couldn't be matched to actual files
- May indicate:
  - Broken references to non-existent code
  - Generic examples (not real code paths)
  - API/library references (external to project)

### How it's used

When code changes are detected, `docmgr_sync` uses these mappings to identify which documentation files may need updates based on what code they reference.

### Safe to edit

**No** - Auto-generated by analyzing markdown content and source code. Changes will be lost on next update.

---

## .doc-manager/memory/doc-conventions.yml

**Purpose**: Defines documentation standards and quality rules for your project.

**When created**: `docmgr_init` (creates with opinionated defaults)

**Format**: YAML

### Structure

```yaml
style:
  headings:
    case: sentence_case           # sentence_case | title_case | lower | upper
    consistency_required: true

  code:
    inline_format: backticks      # backticks | html
    block_language_required: true

  voice:
    person: second                # first | second | third
    active_voice_preferred: true

structure:
  require_intro: true
  require_toc:
    enabled: true
    min_length: 500               # words
  max_heading_depth: 3            # 1-6
  heading_hierarchy: strict       # strict | relaxed

quality:
  sentences:
    max_length: 25                # words
    min_length: 3

  paragraphs:
    max_length: 150               # words

  links:
    validate_links: true

  images:
    require_alt_text: true

  code:
    validate_syntax: false        # Expensive, requires TreeSitter

terminology:
  preferred: {}                   # Define project-specific terms
  avoid:
    - "simply"
    - "just"
    - "easy"
    - "obviously"
```

### How it's used

- `docmgr_validate_docs` checks documentation against these conventions
- `docmgr_assess_quality` uses these rules to score documentation quality
- Violations are reported with severity levels (error, warning, info)

### Customization

Edit this file to match your team's documentation standards:

**Heading style**: If your project uses Title Case headings, change:
```yaml
style:
  headings:
    case: title_case
```

**Terminology**: Define preferred terms for consistency:
```yaml
terminology:
  preferred:
    api:
      full_form: "Application Programming Interface"
      abbreviation: "API"
      guidance: "Spell out on first use, abbreviate after"
```

**Lax structure**: Allow flexible heading hierarchies:
```yaml
structure:
  heading_hierarchy: relaxed  # Allows skipping levels (H1→H3)
```

### Safe to edit

**Yes** - This file is meant to be customized. Changes take effect immediately in validation and quality assessment.
