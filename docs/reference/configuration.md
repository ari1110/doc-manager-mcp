# Configuration reference

## Configuration file

Documentation Manager uses `.doc-manager.yml` in your project root for configuration.

**Location**: `<project-root>/.doc-manager.yml`
**Format**: YAML

The file is automatically created by `docmgr_init` with helpful examples and comments.

## Configuration options

### Platform

- **Type**: string
- **Default**: Auto-detected based on project
- **Required**: Yes
- **Description**: Documentation platform being used

**Supported platforms**:
- `mkdocs` - MkDocs (Python projects)
- `sphinx` - Sphinx (Python projects)
- `hugo` - Hugo (Go projects)
- `docusaurus` - Docusaurus (JavaScript/TypeScript projects)
- `vitepress` - VitePress (Vue projects)
- `unknown` - Generic markdown documentation

**Example:**
```yaml
platform: mkdocs
```

### Exclude

- **Type**: list[string]
- **Default**: `[]`
- **Required**: No
- **Description**: Glob patterns for files/directories to exclude from tracking

**Example:**
```yaml
exclude:
  - "tests/**"
  - "**/__pycache__/**"
  - "**/*.pyc"
  - ".venv/**"
  - "node_modules/**"
```

### Use gitignore

- **Type**: boolean
- **Default**: `false`
- **Required**: No (opt-in feature)
- **Description**: Automatically exclude files based on `.gitignore` patterns

When enabled, files ignored by git will also be excluded from documentation tracking. This prevents you from having to re-enter exclusion patterns that already exist in your `.gitignore` file.

**Priority order**: User excludes > `.gitignore` > built-in defaults

**Example:**
```yaml
use_gitignore: true
exclude:
  - "specs/**"  # Additional patterns beyond .gitignore
```

**How it works**:
1. Built-in default patterns are applied (like `.git/`, `__pycache__/`)
2. If `use_gitignore: true`, patterns from `.gitignore` are applied
3. User-defined `exclude` patterns are applied last (highest priority)

This means user `exclude` patterns can override both `.gitignore` and built-in defaults.

**Notes**:
- Only the root `.gitignore` file is used (nested `.gitignore` files are ignored)
- Uses `pathspec` library with git's native pattern matching (`gitwildmatch`)
- Patterns are parsed from `.gitignore` as-is (comments and blank lines are ignored)
- If `.gitignore` doesn't exist, this setting has no effect

### Sources

- **Type**: list[string]
- **Default**: `[]`
- **Required**: No, but recommended
- **Description**: **Glob patterns** specifying which source files to track for symbol extraction

**IMPORTANT**: Must use glob patterns (e.g., `"src/**/*.py"`), not plain directory names like `"src"`!

**Example:**
```yaml
sources:
  - "src/**/*.py"              # All Python files in src/
  - "lib/**/*.{js,ts}"         # JavaScript and TypeScript in lib/
  - "packages/**/src/**/*.go"  # Go files in monorepo packages
```

**Common mistake:**
```yaml
sources:
  - "src"  # ✗ Wrong - this won't work!
```

### Docs path

- **Type**: string
- **Default**: `"docs"`
- **Required**: Yes
- **Description**: Path to documentation directory (relative to project root)

**Example:**
```yaml
docs_path: docs
```

### Metadata

- **Type**: object
- **Default**: Auto-generated
- **Required**: No (auto-generated)
- **Description**: Project metadata (language, created date, version)

**Example:**
```yaml
metadata:
  language: Python
  created: '2025-11-20T20:22:51.007874'
  version: 1.0.0
```

### API coverage

- **Type**: object
- **Default**: Not set (uses defaults)
- **Required**: No
- **Description**: Configure how public API symbols are detected for documentation coverage metrics

The `api_coverage` section controls which code symbols (functions, classes, etc.) are considered "public" and should be documented. This affects the accuracy percentage shown in quality assessments.

**Quick example:**
```yaml
api_coverage:
  preset: pydantic      # Filter framework symbols
  strategy: all_only    # Only count __all__ exports
```

**Key options:**
- `strategy` - How to determine public symbols (`all_then_underscore`, `all_only`, `underscore_only`)
- `preset` - Pre-configured exclusions for common frameworks (pydantic, django, jest, etc.)
- `exclude_symbols` - Custom patterns to exclude
- `include_symbols` - Force-include specific symbols

For complete documentation of all options, presets, and examples, see [API Coverage Reference](api-coverage.md).

## Configuration examples

### Example 1: Python project with MkDocs

```yaml
platform: mkdocs
use_gitignore: true
exclude:
  - "tests/**"
  - "specs/**"  # Additional exclusions beyond .gitignore
sources:
  - "src/**/*.py"
  - "lib/**/*.py"
docs_path: docs
metadata:
  language: Python
  created: '2025-11-20T20:22:51.007874'
  version: 1.0.0
```

### Example 2: JavaScript monorepo with Docusaurus

```yaml
platform: docusaurus
use_gitignore: true
exclude:
  - "**/*.test.{js,ts}"  # Exclude test files beyond .gitignore
sources:
  - "packages/*/src/**/*.{js,ts,tsx}"
  - "apps/*/src/**/*.{js,ts,tsx}"
docs_path: website/docs
metadata:
  language: JavaScript
  created: '2025-11-20T15:30:00.000000'
  version: 1.0.0
```

### Example 3: Go project with Hugo

```yaml
platform: hugo
use_gitignore: true
exclude:
  - "**/testdata/**"  # Additional exclusions beyond .gitignore
  - "**/*_test.go"
sources:
  - "cmd/**/*.go"
  - "pkg/**/*.go"
  - "internal/**/*.go"
docs_path: docs
metadata:
  language: Go
  created: '2025-11-20T18:45:00.000000'
  version: 1.0.0
```

## Glob pattern syntax

Documentation Manager uses standard glob patterns:

| Pattern | Matches | Example |
|---------|---------|---------|
| `*` | Any characters except `/` | `*.py` matches `file.py` |
| `**` | Any characters including `/` | `src/**/*.py` matches `src/a/b.py` |
| `?` | Single character | `file?.py` matches `file1.py` |
| `[abc]` | Character class | `file[123].py` matches `file1.py` |
| `{a,b}` | Alternatives | `*.{js,ts}` matches `.js` and `.ts` |

## Best practices

### Use .gitignore integration

Enable `use_gitignore: true` to avoid duplicating exclusion patterns:

```yaml
use_gitignore: true
exclude:
  - "specs/**"  # Only add patterns NOT in .gitignore
```

**Benefits**:
- No need to duplicate patterns from `.gitignore`
- Automatically excludes `node_modules/`, `venv/`, build artifacts, etc.
- Consistent exclusion rules between git and doc-manager

**When to add explicit excludes**:
- Project-specific patterns not in `.gitignore`
- Documentation-specific exclusions (like `specs/`)
- Override `.gitignore` patterns for documentation purposes

### Start specific, expand later

Begin with specific source patterns and expand as needed:

```yaml
# Start here
sources:
  - "src/**/*.py"

# Expand later
sources:
  - "src/**/*.py"
  - "lib/**/*.py"
  - "tools/**/*.py"
```

### Use extensions to filter

Include file extensions in patterns to avoid matching non-source files:

```yaml
sources:
  - "src/**/*.{py,pyi}"  # Python source and stubs only
```

### Exclude test files

Always exclude test files to focus on production code:

```yaml
exclude:
  - "tests/**"
  - "**/*_test.py"
  - "**/*.test.js"
```

### Version control configuration

The `.doc-manager.yml` file should be committed to version control, but the `.doc-manager/` directory should be excluded (added to `.gitignore`):

```gitignore
.doc-manager/
```

## Troubleshooting

Having configuration issues? See the [Troubleshooting guide](../guides/troubleshooting.md#configuration-issues) for solutions to symbol extraction, file tracking, platform detection, and baseline issues.
