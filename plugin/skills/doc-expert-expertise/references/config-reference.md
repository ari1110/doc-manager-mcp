# Configuration Reference

Complete reference for `.doc-manager.yml` configuration options.

## File Location

Configuration file: `<project_root>/.doc-manager.yml`

## Core Options

### platform

Documentation platform type.

| Value | Description |
|-------|-------------|
| `mkdocs` | MkDocs (Python-based) |
| `sphinx` | Sphinx documentation |
| `docusaurus` | Docusaurus (React-based) |
| `hugo` | Hugo static site generator |
| `vitepress` | VitePress (Vue-based) |
| `jekyll` | Jekyll static site generator |
| `gitbook` | GitBook |
| `markdown` | Plain markdown (no platform) |
| `unknown` | Unknown/other |

**Default**: Auto-detected from project files

### docs_path

Path to documentation directory (relative to project root).

**Type**: `string`
**Default**: Auto-detected (`docs/`, `documentation/`, etc.)
**Example**: `docs_path: docs`

### sources

Glob patterns for source files to track for documentation coverage.

**Type**: `list[string]`
**Default**: Auto-detected based on project language
**Example**:
```yaml
sources:
  - "src/**/*.py"
  - "lib/**/*.ts"
```

### exclude

Glob patterns for files to exclude from tracking.

**Type**: `list[string]`
**Default**: Common patterns (tests, cache, build artifacts)
**Example**:
```yaml
exclude:
  - "tests/**"
  - "**/__pycache__/**"
  - "dist/**"
  - ".venv/**"
```

### use_gitignore

Automatically exclude files based on `.gitignore` patterns.

**Type**: `boolean`
**Default**: `false`

When enabled, files ignored by git are also excluded from doc tracking.
Priority: user excludes > .gitignore > built-in defaults

### include_root_readme

Include root `README.md` in documentation operations.

**Type**: `boolean`
**Default**: `false`

When enabled, validation, quality assessment, and change detection include the root README.md alongside docs in the docs/ directory.

---

## api_coverage Section

Controls how public API symbols are detected and filtered for documentation coverage metrics.

### api_coverage.strategy

How to determine which symbols are "public" and should be documented.

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `all_then_underscore` | Use `__all__` if defined, else underscore convention | **Default** - Libraries, general projects |
| `all_only` | Only symbols in `__all__` are public | MCP servers, internal tools, strict API control |
| `underscore_only` | Only use underscore convention, ignore `__all__` | Legacy projects, loose conventions |

**Default**: `all_then_underscore`

**Choosing the right strategy:**

| Project Type | Recommended Strategy | Rationale |
|--------------|---------------------|-----------|
| Library/SDK | `all_then_underscore` | Users import your API directly |
| MCP Server | `all_only` | Users interact via protocol, not Python imports |
| CLI Tool | `all_only` or `underscore_only` | Users interact via commands |
| Application | `all_only` | Internal code, minimal public API |

### api_coverage.preset

Pre-configured exclusion patterns for common frameworks.

**Type**: `string | null`
**Default**: `null` (no preset)

#### Python Presets

| Preset | Excludes | Use When |
|--------|----------|----------|
| `pydantic` | `Config`, `model_config`, `model_validator`, `field_validator`, `root_validator`, `validator`, `validate_*` | Using Pydantic models |
| `django` | `Meta`, `DoesNotExist`, `MultipleObjectsReturned` | Django ORM models |
| `fastapi` | `Config`, `model_config` | FastAPI with Pydantic |
| `pytest` | `test_*`, `Test*`, `fixture`, `conftest` | Test files in coverage |
| `sqlalchemy` | `metadata`, `__table__`, `__tablename__`, `__mapper__`, `_sa_*`, `registry` | SQLAlchemy models |

#### JavaScript/TypeScript Presets

| Preset | Excludes | Use When |
|--------|----------|----------|
| `jest` | `describe`, `it`, `test`, `beforeEach`, `afterEach`, `beforeAll`, `afterAll`, `expect` | Jest test files |
| `vitest` | `describe`, `it`, `test`, `suite`, `beforeEach`, `afterEach`, `beforeAll`, `afterAll`, `expect`, `vi` | Vitest test files |
| `react` | `_render*`, `UNSAFE_*`, `__*`, `$$typeof` | React internal symbols |
| `vue` | `$_*`, `__v*`, `_c`, `_h`, `_s`, `_v`, `_e`, `_m`, `_l` | Vue internal symbols |

#### Go Presets

| Preset | Excludes | Use When |
|--------|----------|----------|
| `go-test` | `Test*`, `Benchmark*`, `Example*`, `Fuzz*` | Go test functions |

#### Rust Presets

| Preset | Excludes | Use When |
|--------|----------|----------|
| `rust-test` | `tests`, `test_*`, `bench_*` | Rust test modules |
| `serde` | `Serialize`, `Deserialize`, `__serde_*` | Serde derive traits |

### api_coverage.exclude_symbols

Custom patterns for symbols to exclude (in addition to preset).

**Type**: `list[string]`
**Default**: `[]`

Uses fnmatch (shell-style) pattern matching:
- `*` matches everything
- `?` matches single character
- `[seq]` matches any character in seq
- `[!seq]` matches any character NOT in seq

**Example**:
```yaml
api_coverage:
  exclude_symbols:
    - "Internal*"
    - "_private_*"
    - "deprecated_*"
```

### api_coverage.include_symbols

Patterns for symbols to force-include (overrides exclusions).

**Type**: `list[string]`
**Default**: `[]`

Use this to whitelist specific symbols that would otherwise be excluded.

**Example**:
```yaml
api_coverage:
  preset: pydantic
  include_symbols:
    - "MySpecialConfig"  # Include even though preset excludes *Config
```

---

## Configuration Examples

### Python Library

```yaml
platform: mkdocs
docs_path: docs
sources:
  - "src/**/*.py"
exclude:
  - "tests/**"
  - "**/__pycache__/**"
api_coverage:
  preset: pydantic
  strategy: all_then_underscore
```

### MCP Server

```yaml
platform: markdown
docs_path: docs
sources:
  - "my_server/**/*.py"
exclude:
  - "tests/**"
api_coverage:
  preset: pydantic
  strategy: all_only  # Users interact via MCP protocol, not Python API
```

### React Application

```yaml
platform: docusaurus
docs_path: docs
sources:
  - "src/**/*.tsx"
  - "src/**/*.ts"
exclude:
  - "**/*.test.tsx"
  - "**/*.spec.ts"
api_coverage:
  preset: react
  strategy: underscore_only
```

### Go Project

```yaml
platform: hugo
docs_path: docs
sources:
  - "**/*.go"
exclude:
  - "vendor/**"
  - "**/*_test.go"
api_coverage:
  preset: go-test
  strategy: all_then_underscore
```

### Multi-Framework Python

```yaml
platform: sphinx
docs_path: docs
sources:
  - "app/**/*.py"
api_coverage:
  preset: fastapi  # Base preset
  exclude_symbols:
    # Additional SQLAlchemy patterns
    - "metadata"
    - "__table__"
    - "__tablename__"
    # Custom internal patterns
    - "_internal_*"
```

---

## Troubleshooting

### Low API coverage percentage

**Symptom**: Quality assessment shows low coverage (e.g., 26%)

**Causes & Solutions**:

1. **Framework symbols inflating count**: Add appropriate preset
   ```yaml
   api_coverage:
     preset: pydantic
   ```

2. **Wrong strategy for project type**: MCP servers should use `all_only`
   ```yaml
   api_coverage:
     strategy: all_only
   ```

3. **Test symbols included**: Exclude test patterns
   ```yaml
   api_coverage:
     exclude_symbols:
       - "test_*"
       - "Test*"
   ```

### 0% coverage (no public symbols)

**Symptom**: `api_coverage: 0%` with "No public symbols found"

**This is correct if**:
- Using `all_only` strategy AND no `__all__` is defined
- Project is an MCP server or internal tool

**This is a problem if**:
- You're building a library and expect public API
- Solution: Switch to `all_then_underscore` or define `__all__` in your modules

### Preset not filtering expected symbols

**Symptom**: Framework symbols still appear as undocumented

**Check**:
1. Preset name is spelled correctly
2. Symbol names match preset patterns exactly
3. Custom `include_symbols` isn't overriding the exclusion
