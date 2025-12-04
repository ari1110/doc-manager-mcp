# Project Context

## Purpose

**doc-manager-mcp** is a comprehensive documentation lifecycle management tool powered by an MCP (Model Context Protocol) server. It enables AI assistants to:

- Automatically detect code changes and identify affected documentation
- Validate documentation for broken links, missing assets, and syntax errors
- Assess documentation quality against 7 criteria (relevance, accuracy, purposefulness, uniqueness, consistency, clarity, structure)
- Track code-to-docs dependencies using TreeSitter-based symbol extraction
- Support documentation migration with git history preservation
- Auto-detect documentation platforms (MkDocs, Sphinx, Hugo, Docusaurus, etc.)

The project is distributed via PyPI as `doc-manager-mcp` and can be used standalone or as a Claude Code plugin.

## Tech Stack

### Core
- **Python 3.10+** - Minimum supported version
- **FastMCP (mcp>=1.0.0)** - MCP server framework
- **Pydantic 2.0+** - Data validation and settings management
- **PyYAML 6.0+** - YAML configuration parsing

### Analysis & Parsing
- **tree-sitter>=0.21.0** - Code symbol extraction (AST parsing)
- **tree-sitter-language-pack>=0.1.0** - Language grammars (Python, Go, TypeScript, Rust)
- **markdown-it-py>=4.0.0** - Markdown parsing
- **python-frontmatter>=1.1.0** - YAML frontmatter extraction

### Build & Quality
- **Hatchling** - Build backend
- **Ruff>=0.14.5** - Linting and formatting
- **Pyright>=1.1.407** - Static type checking
- **pytest>=9.0.1** - Testing framework
- **pytest-asyncio>=1.3.0** - Async test support
- **pytest-cov>=7.0.0** - Coverage reporting

## Project Conventions

### Code Style

- **Line length**: 100 characters (enforced by Ruff)
- **Target version**: Python 3.10
- **Imports**: Sorted via isort (Ruff I rules)
- **Naming**: PEP 8 conventions (snake_case for functions/variables, PascalCase for classes)
- **Type hints**: Required for all public APIs (enforced by Pyright)
- **Docstrings**: Google style for public functions and classes

**Ruff rules enabled**:
- E, W: pycodestyle errors/warnings
- F: pyflakes
- I: isort
- N: pep8-naming
- UP: pyupgrade (modern Python syntax)
- B: flake8-bugbear
- S: flake8-bandit (security)
- C4: flake8-comprehensions
- PIE, RUF: misc lints

### Architecture Patterns

**Package Structure**:
```
doc_manager_mcp/
├── server.py              # FastMCP server with tool registration
├── models.py              # Pydantic input models with validation
├── constants.py           # Enums (ChangeDetectionMode, DocumentationPlatform, QualityCriterion)
├── core/                  # Core utilities (paths, git, checksums, security)
├── tools/                 # Tool implementations
│   ├── analysis/          # Read-only analysis tools
│   │   ├── quality/       # 7-criterion quality assessment
│   │   └── validation/    # Link, asset, snippet validation
│   ├── state/             # State management (init, update_baseline)
│   └── workflows/         # Orchestration (sync, migrate)
├── indexing/              # Code/doc indexing
│   ├── analysis/          # TreeSitter, semantic diff
│   ├── parsers/           # Markdown parsing
│   └── transforms/        # Link rewriting
└── schemas/               # Config and baseline schemas
```

**Tool Architecture**:
- Tools are registered via `@mcp.tool` decorator in `server.py`
- Each tool has a Pydantic input model in `models.py`
- Tool implementations live in `tools/` subdirectories
- Read-only tools are clearly marked with `readOnlyHint=True`

**Baseline System**:
Three baseline files in `.doc-manager/memory/`:
1. `repo-baseline.json` - File checksums and metadata
2. `symbol-baseline.json` - TreeSitter code symbols
3. `dependencies.json` - Code-to-docs mappings

### Testing Strategy

**Test Structure**:
```
tests/
├── unit/          # Unit tests for individual components
├── integration/   # Integration tests for workflows
└── fixtures/      # Sample project files for testing
```

**Running Tests**:
```bash
uv run pytest                          # All tests
uv run pytest tests/unit/              # Unit tests only
uv run pytest --cov=doc_manager_mcp    # With coverage
```

**Test Requirements**:
- All new tools must have unit tests
- Integration tests for multi-tool workflows
- Security-related code requires extra scrutiny

### Git Workflow

**Branch**: Main branch is `main`

**Commit Message Format**:
```
<type>: <description>

<body explaining changes>

<phase reference if applicable>

Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**: feat, fix, chore, docs, refactor, test

**Commit Frequency**: After each task/phase completion, especially during spec implementation.

## Domain Context

### MCP (Model Context Protocol)
MCP is a protocol that allows AI assistants to interact with external tools. This project provides 8 MCP tools:

1. **docmgr_init** - Initialize doc-manager (modes: existing, bootstrap)
2. **docmgr_detect_changes** - Detect code changes (read-only)
3. **docmgr_detect_platform** - Auto-detect documentation platform
4. **docmgr_validate_docs** - Validate links, assets, snippets
5. **docmgr_assess_quality** - Quality assessment (7 criteria)
6. **docmgr_update_baseline** - Update all baselines atomically
7. **docmgr_sync** - Orchestrate sync workflow (check/resync modes)
8. **docmgr_migrate** - Migrate docs with git history preservation

### Documentation Platforms Supported
- MkDocs (mkdocs.yml)
- Sphinx (conf.py)
- Hugo (config.toml)
- Docusaurus (docusaurus.config.js)
- VitePress
- Jekyll
- GitBook

### Quality Criteria
The 7 quality criteria for documentation assessment:
1. **Relevance** - Addresses current user needs
2. **Accuracy** - Reflects actual codebase state
3. **Purposefulness** - Clear goals and target audience
4. **Uniqueness** - No redundant or conflicting information
5. **Consistency** - Aligned terminology, formatting, style
6. **Clarity** - Precise language and navigation
7. **Structure** - Logical organization and hierarchy

## Important Constraints

### Security
- **Path traversal prevention**: All paths validated to prevent `..` sequences
- **Command injection prevention**: Git commit hashes validated (7-40 hex chars only)
- **ReDoS prevention**: Glob patterns validated against dangerous nested quantifiers
- **Pattern limits**: Max 50 patterns, max 512 chars per pattern

### Performance
- Incremental validation supported for large codebases
- TreeSitter-based semantic analysis can be expensive (opt-in via `include_semantic`)
- Markdown cache for repeated parsing operations

### Compatibility
- Windows: Requires ProactorEventLoop for subprocess support (auto-configured)
- Cross-platform path handling via pathlib

## External Dependencies

### PyPI Distribution
- Package name: `doc-manager-mcp`
- Entry point: `doc-manager-mcp` command
- Installation: `pip install doc-manager-mcp` or `uvx doc-manager-mcp`

### Claude Code Plugin
The project can be installed as a Claude Code plugin from the marketplace:
```bash
/plugin marketplace add ari1110/doc-manager-mcp
/plugin install doc-manager@doc-manager-suite
```

### File System
- Configuration: `.doc-manager.yml` at project root
- Memory/state: `.doc-manager/memory/` directory
- Conventions: `.doc-manager/doc-conventions.yml` (optional)
