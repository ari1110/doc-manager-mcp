# API coverage reference

The `api_coverage` configuration controls how public API symbols are detected and filtered for documentation coverage metrics.

## Why use api_coverage

By default, Documentation Manager counts all non-underscore-prefixed symbols as "public" and includes them in coverage metrics. This can lead to misleading results:

- **Framework symbols inflate counts**: Pydantic's `Config` class, Django's `Meta` class, etc. appear as "undocumented"
- **Wrong strategy for project type**: An MCP server has no public Python API, but default settings report low coverage
- **Test symbols included**: `test_*` functions appear in the undocumented list

The `api_coverage` section lets you tune these metrics for accurate results.

## Configuration options

### Strategy

The `strategy` option determines which symbols are "public" and should be documented.

```yaml
api_coverage:
  strategy: all_then_underscore  # default
```

| Strategy | Description | Best for |
|----------|-------------|----------|
| `all_then_underscore` | Use `__all__` if defined, else underscore convention | Libraries, SDKs |
| `all_only` | Only symbols in `__all__` are public | MCP servers, internal tools |
| `underscore_only` | Only use underscore convention, ignore `__all__` | Legacy projects |

**Default**: `all_then_underscore`

#### Choosing the right strategy

| Project type | Recommended strategy | Rationale |
|--------------|---------------------|-----------|
| Library/SDK | `all_then_underscore` | Users import your API directly |
| MCP server | `all_only` | Users interact via protocol, not Python |
| CLI tool | `all_only` | Users interact via commands |
| Application | `all_only` | Internal code, minimal public API |

### Preset

The `preset` option provides pre-configured exclusion patterns for common frameworks.

```yaml
api_coverage:
  preset: pydantic
```

#### Python presets

| Preset | Excludes | Use when |
|--------|----------|----------|
| `pydantic` | `Config`, `model_config`, `model_validator`, `field_validator`, `root_validator`, `validator`, `validate_*` | Using Pydantic models |
| `django` | `Meta`, `DoesNotExist`, `MultipleObjectsReturned` | Django ORM models |
| `fastapi` | `Config`, `model_config` | FastAPI with Pydantic |
| `pytest` | `test_*`, `Test*`, `fixture`, `conftest` | Test files in coverage |
| `sqlalchemy` | `metadata`, `__table__`, `__tablename__`, `__mapper__`, `_sa_*`, `registry` | SQLAlchemy models |

#### JavaScript/TypeScript presets

| Preset | Excludes | Use when |
|--------|----------|----------|
| `jest` | `describe`, `it`, `test`, `beforeEach`, `afterEach`, `beforeAll`, `afterAll`, `expect` | Jest test files |
| `vitest` | `describe`, `it`, `test`, `suite`, `beforeEach`, `afterEach`, `beforeAll`, `afterAll`, `expect`, `vi` | Vitest test files |
| `react` | `_render*`, `UNSAFE_*`, `__*`, `$$typeof` | React internal symbols |
| `vue` | `$_*`, `__v*`, `_c`, `_h`, `_s`, `_v`, `_e`, `_m`, `_l` | Vue internal symbols |

#### Go presets

| Preset | Excludes | Use when |
|--------|----------|----------|
| `go-test` | `Test*`, `Benchmark*`, `Example*`, `Fuzz*` | Go test functions |

#### Rust presets

| Preset | Excludes | Use when |
|--------|----------|----------|
| `rust-test` | `tests`, `test_*`, `bench_*` | Rust test modules |
| `serde` | `Serialize`, `Deserialize`, `__serde_*` | Serde derive traits |

### Exclude symbols

The `exclude_symbols` option defines custom patterns for symbols to exclude (in addition to preset).

```yaml
api_coverage:
  exclude_symbols:
    - "Internal*"
    - "_private_*"
    - "deprecated_*"
```

Uses fnmatch (shell-style) pattern matching:
- `*` matches everything
- `?` matches single character
- `[seq]` matches any character in seq
- `[!seq]` matches any character NOT in seq

### Include symbols

The `include_symbols` option defines patterns for symbols to force-include (overrides exclusions).

```yaml
api_coverage:
  preset: pydantic
  include_symbols:
    - "MySpecialConfig"  # Include even though preset excludes *Config
```

## Configuration examples

### Python library with Pydantic

```yaml
api_coverage:
  preset: pydantic
  strategy: all_then_underscore
```

### MCP server

```yaml
api_coverage:
  preset: pydantic
  strategy: all_only  # Users interact via MCP protocol
```

### FastAPI + SQLAlchemy application

```yaml
api_coverage:
  preset: fastapi
  exclude_symbols:
    # Additional SQLAlchemy patterns
    - "metadata"
    - "__table__"
    - "__tablename__"
```

### React application

```yaml
api_coverage:
  preset: react
  strategy: underscore_only
```

### Go project with tests

```yaml
api_coverage:
  preset: go-test
  strategy: all_then_underscore
```

### Multi-framework Python project

```yaml
api_coverage:
  preset: pydantic
  exclude_symbols:
    # Django patterns
    - "Meta"
    - "DoesNotExist"
    # pytest patterns
    - "test_*"
    - "Test*"
    # Custom internal patterns
    - "_internal_*"
```

## Troubleshooting

### Low API coverage percentage

**Symptom**: Quality assessment shows low coverage (e.g., 26%)

**Possible causes**:

1. **Framework symbols inflating count**

   Add the appropriate preset:
   ```yaml
   api_coverage:
     preset: pydantic  # or django, fastapi, etc.
   ```

2. **Wrong strategy for project type**

   For MCP servers or applications:
   ```yaml
   api_coverage:
     strategy: all_only
   ```

3. **Test symbols included**

   Exclude test patterns:
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
- **Solution**: Switch to `all_then_underscore` or define `__all__` in your modules

### Preset not filtering expected symbols

**Symptom**: Framework symbols still appear as undocumented

**Check**:
1. Preset name is spelled correctly (case-sensitive)
2. Symbol names match preset patterns exactly
3. Custom `include_symbols` isn't overriding the exclusion

### Coverage didn't change after config update

**Possible causes**:

1. **Baseline not updated**

   Run `docmgr_update_baseline` after config changes

2. **Pattern syntax incorrect**

   Uses fnmatch, not regex. Example: `test_*` not `test_.*`

3. **Preset name misspelled**

   Check available presets in this reference

## Pattern syntax reference

The `exclude_symbols` and `include_symbols` options use fnmatch (shell-style) patterns:

| Pattern | Matches | Example |
|---------|---------|---------|
| `*` | Any characters | `test_*` matches `test_foo`, `test_bar` |
| `?` | Single character | `file?` matches `file1`, `fileA` |
| `[seq]` | Any char in seq | `file[123]` matches `file1`, `file2`, `file3` |
| `[!seq]` | Any char NOT in seq | `file[!0-9]` matches `fileA`, `fileB` |
| Literal | Exact match | `Config` matches only `Config` |

**Examples**:
- `test_*` - All symbols starting with `test_`
- `*Config` - All symbols ending with `Config`
- `_*` - All symbols starting with underscore
- `__*__` - All dunder methods
