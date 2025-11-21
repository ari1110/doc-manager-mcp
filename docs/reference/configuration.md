# Configuration reference

## Configuration file

Documentation Manager uses `.doc-manager.yml` in your project root for configuration.

**Location**: `<project-root>/.doc-manager.yml`
**Format**: YAML

The file is automatically created by `docmgr_init` with helpful examples and comments.

## Configuration options

### platform

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

### exclude

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

### sources

- **Type**: list[string]
- **Default**: `[]`
- **Required**: No, but recommended
- **Description**: **Glob patterns** specifying which source files to track for symbol extraction

**IMPORTANT**: Must use glob patterns (e.g., `"src/**/*.py"`), not just directory names!

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

### docs_path

- **Type**: string
- **Default**: `"docs"`
- **Required**: Yes
- **Description**: Path to documentation directory (relative to project root)

**Example:**
```yaml
docs_path: docs
```

### metadata

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

## Configuration examples

### Example 1: Python project with MkDocs

```yaml
platform: mkdocs
exclude:
  - "tests/**"
  - "**/__pycache__/**"
  - ".venv/**"
  - "dist/**"
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
exclude:
  - "node_modules/**"
  - "**/dist/**"
  - "**/*.test.{js,ts}"
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
exclude:
  - "vendor/**"
  - "**/testdata/**"
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

### Symbols not being extracted

If `symbol-baseline.json` is empty:
1. Verify `sources` uses **glob patterns**, not directory names
2. Check patterns match your files: test with `ls src/**/*.py`
3. Ensure no exclude patterns are blocking your sources

### Too many files tracked

If tracking too many files:
1. Add specific exclude patterns
2. Make source patterns more restrictive
3. Check `repo-baseline.json` to see what's being tracked
