# Enums reference

**Module:** `doc_manager_mcp.constants`

Complete reference for all enumerations in the doc-manager MCP server.

---

## DocumentationPlatform

Supported documentation platforms.

**Module**: `doc_manager_mcp.constants`

**Enum Class**: `DocumentationPlatform(str, Enum)`

All values are strings and can be used interchangeably with string literals.

### Values

| Value | Alias | Description |
|-------|-------|-------------|
| `hugo` | `DocumentationPlatform.HUGO` | Static site generator written in Go. Fast, language-agnostic, popular in Go ecosystem |
| `docusaurus` | `DocumentationPlatform.DOCUSAURUS` | React-based documentation generator. Popular in JavaScript/TypeScript ecosystem |
| `mkdocs` | `DocumentationPlatform.MKDOCS` | Python-based static site generator. Popular in Python ecosystem |
| `sphinx` | `DocumentationPlatform.SPHINX` | Documentation generator with reStructuredText support. Standard for Python projects |
| `vitepress` | `DocumentationPlatform.VITEPRESS` | Vue-powered static site generator. Fast, modern, TypeScript-friendly |
| `jekyll` | `DocumentationPlatform.JEKYLL` | Simple static site generator written in Ruby. GitHub Pages native support |
| `gitbook` | `DocumentationPlatform.GITBOOK` | Documentation platform with version control. Good for team collaboration |
| `unknown` | `DocumentationPlatform.UNKNOWN` | Platform could not be detected automatically |

### When to use each platform

**Hugo** - For language-agnostic projects, Go projects, or when maximum performance is critical

**Docusaurus** - For JavaScript/TypeScript projects, React-based sites, or teams familiar with Node.js

**MkDocs** - For Python projects, or when you want a simple, lightweight documentation solution

**Sphinx** - For Python projects requiring sophisticated documentation (API docs, cross-references), or academic/technical documentation

**Vitepress** - For Vue/TypeScript projects, or when you want modern tooling with fast builds

**Jekyll** - For projects hosted on GitHub Pages, or when you prefer Ruby-based tools

**Gitbook** - For team-collaborative documentation, or when you need built-in versioning and publishing

### Usage examples

```python
from doc_manager_mcp.constants import DocumentationPlatform

# Using enum directly
platform = DocumentationPlatform.MKDOCS

# Converting from string
platform = DocumentationPlatform("sphinx")

# Checking platform
if platform == DocumentationPlatform.PYTHON:
    print("Python-friendly")

# Iterating all platforms
for platform in DocumentationPlatform:
    if platform != DocumentationPlatform.UNKNOWN:
        print(f"Supported: {platform.value}")

# Input to tools
from doc_manager_mcp.models import DocmgrInitInput

init = DocmgrInitInput(
    project_path="/path/to/project",
    platform=DocumentationPlatform.MKDOCS
)
```

### Platform detection

When `platform` parameter is `None`, doc-manager will auto-detect based on:

1. **Configuration files** - Look for platform-specific config files:
   - Hugo: `hugo.toml`, `hugo.yaml`, `config.toml`
   - Docusaurus: `docusaurus.config.js`, `docusaurus.config.ts`
   - MkDocs: `mkdocs.yml`
   - Sphinx: `docs/conf.py` or `doc/conf.py`
   - Vitepress: `.vitepress/config.js`, `.vitepress/config.ts`
   - Jekyll: `_config.yml`

2. **Dependencies** - Check dependency files:
   - Hugo: Look for `hugo` in `go.mod`
   - Docusaurus: Look for `docusaurus` or `@docusaurus/core` in `package.json`
   - MkDocs: Look for `mkdocs` in `requirements.txt`
   - Sphinx: Look for `sphinx` in `requirements.txt` or `setup.py`
   - Vitepress: Look for `vitepress` in `package.json`

3. **Language recommendation** - Fall back to language-based recommendations:
   - Go projects: Hugo
   - JavaScript/TypeScript/Node.js: Docusaurus
   - Python: MkDocs

4. **Default** - If no platform detected: Hugo (fast, language-agnostic)

### Platform configuration

Each platform has detection markers defined in `PLATFORM_MARKERS`:

```python
PLATFORM_MARKERS = {
    "hugo": {
        "root_configs": ["hugo.toml", "hugo.yaml", "config.toml"],
        "subdir_configs": ["hugo.yaml", "hugo.toml", "config.toml"],
        "dependencies": {"go.mod": ["hugo"]},
    },
    "docusaurus": {
        "root_configs": ["docusaurus.config.js", "docusaurus.config.ts"],
        "subdir_configs": ["docusaurus.config.js", "docusaurus.config.ts"],
        "dependencies": {"package.json": ["docusaurus", "@docusaurus/core"]},
    },
    # ... more platforms
}
```

---

## QualityCriterion

Quality assessment criteria for documentation.

**Module**: `doc_manager_mcp.constants`

**Enum Class**: `QualityCriterion(str, Enum)`

Represents the 7 dimensions used to evaluate documentation quality.

### Values

| Value | Alias | Description |
|-------|-------|-------------|
| `relevance` | `QualityCriterion.RELEVANCE` | Documentation addresses actual user needs and use cases. Includes what users actually need to know, not what developers assume is important |
| `accuracy` | `QualityCriterion.ACCURACY` | Information is factually correct and up-to-date. Reflects current API/behavior, no deprecated information, examples actually work |
| `purposefulness` | `QualityCriterion.PURPOSEFULNESS` | Content has clear purpose and value. Each section/paragraph contributes meaningfully. No filler or obvious content |
| `uniqueness` | `QualityCriterion.UNIQUENESS` | Information is not redundant or unnecessarily duplicated. Concepts explained once, not repeated across multiple pages without added value |
| `consistency` | `QualityCriterion.CONSISTENCY` | Style, terminology, and formatting are consistent throughout. Same concepts use same terms, same style of code examples, same heading structure |
| `clarity` | `QualityCriterion.CLARITY` | Content is clear and accessible. Language is precise, sentences are clear, complex concepts are well-explained with examples |
| `structure` | `QualityCriterion.STRUCTURE` | Organization is logical and navigable. Information hierarchy makes sense, navigation is clear, related topics grouped together |

### Assessment scores

Each criterion is typically scored on a scale:

- **Poor** (0-2): Significant issues affecting usability
- **Fair** (2-4): Some issues, partially meets criterion
- **Good** (4-6): Generally meets criterion with minor issues
- **Excellent** (6-10): Fully meets criterion, excellent quality

### When to use

**Relevance** - If documentation doesn't address user needs, nothing else matters. Assess whether:
- Content matches user personas
- Examples solve real problems
- Edge cases are documented

**Accuracy** - Assess whether:
- All code examples work correctly
- API descriptions match current implementation
- No deprecated or outdated information

**Purposefulness** - Assess whether:
- Each section justifies its existence
- No "nice-to-know" that distracts from essential info
- Content density is appropriate

**Uniqueness** - Assess whether:
- Concepts aren't repeated in multiple places
- DRY principle applied to documentation
- Cross-references used instead of duplication

**Consistency** - Assess whether:
- Terminology consistent across all docs
- Code examples follow same patterns
- Formatting/structure consistent

**Clarity** - Assess whether:
- Sentences are concise and clear
- Complex concepts have examples
- Jargon is explained

**Structure** - Assess whether:
- Information organized logically
- Navigation is intuitive
- Table of contents reflects actual content

### Usage examples

```python
from doc_manager_mcp.constants import QualityCriterion
from doc_manager_mcp.models import AssessQualityInput

# Assess all criteria
assess = AssessQualityInput(
    project_path="/path/to/project"
)

# Assess specific criteria
assess = AssessQualityInput(
    project_path="/path/to/project",
    criteria=[
        QualityCriterion.CLARITY,
        QualityCriterion.ACCURACY,
        QualityCriterion.CONSISTENCY
    ]
)

# Iterating all criteria
from doc_manager_mcp.constants import QUALITY_CRITERIA

for criterion in QUALITY_CRITERIA:
    print(f"Assessing: {criterion}")
```

### Typical assessment order

A suggested order for quality assessment:

1. **Structure** - First, ensure organization is sound
2. **Accuracy** - Verify information is correct
3. **Clarity** - Check readability
4. **Consistency** - Verify uniform style/terminology
5. **Relevance** - Confirm content addresses user needs
6. **Uniqueness** - Eliminate redundancy
7. **Purposefulness** - Verify each section justifies existence

---

## ChangeDetectionMode

Modes for detecting changes in code and documentation.

**Module**: `doc_manager_mcp.constants`

**Enum Class**: `ChangeDetectionMode(str, Enum)`

Determines how doc-manager identifies which files have changed.

### Values

| Value | Alias | Description |
|-------|-------|-------------|
| `checksum` | `ChangeDetectionMode.CHECKSUM` | Compare current file checksums against baseline (`repo-baseline.json`). Detects file modifications, additions, deletions. No git history required. Faster for projects with many files |
| `git_diff` | `ChangeDetectionMode.GIT_DIFF` | Compare current state against specific git commit. Requires `since_commit` parameter. Uses git diff information. Better for CI/CD integration |

### Checksum mode

**When to use**: When you want to compare against last recorded state

**Characteristics**:
- Uses file SHA-256 checksums
- Compares against `repo-baseline.json` (stored in `.doc-manager/memory/`)
- No git repository required
- Detects any file change (git tracked or not)
- Includes untracked changes

**Advantages**:
- Works in non-git repositories
- Detects all file changes (including untracked)
- No git history needed
- Fast baseline comparison

**Limitations**:
- Requires `docmgr_init` to create baseline
- Baseline must be manually updated with `docmgr_update_baseline` or `docmgr_sync mode="resync"`

**Example**:

```python
from doc_manager_mcp.constants import ChangeDetectionMode
from doc_manager_mcp.models import DocmgrDetectChangesInput

# Compare against baseline
detect = DocmgrDetectChangesInput(
    project_path="/path/to/project",
    mode=ChangeDetectionMode.CHECKSUM
)
```

### Git diff mode

**When to use**: When you want to compare against a specific git commit (CI/CD pipelines)

**Characteristics**:
- Uses `git diff` command
- Compares current state against `since_commit`
- Requires valid git SHA (7-40 hex characters)
- No baseline file needed
- Git history-based

**Advantages**:
- No baseline files needed
- Integrates well with CI/CD (compare PR against base branch)
- Can compare against any commit
- Works with git workflows

**Limitations**:
- Requires git repository
- Requires valid commit SHA
- Cannot detect untracked files

**Requirements**:
- `since_commit` parameter is required
- Must be valid git commit SHA (7-40 hexadecimal characters)
- Commit must exist in repository

**Example**:

```python
from doc_manager_mcp.constants import ChangeDetectionMode
from doc_manager_mcp.models import DocmgrDetectChangesInput

# Compare against commit
detect = DocmgrDetectChangesInput(
    project_path="/path/to/project",
    mode=ChangeDetectionMode.GIT_DIFF,
    since_commit="abc123def456"  # Valid git SHA
)
```

### Common mistake: mode parameter format

When specifying mode as a string, use underscore, not hyphen:

```python
# Correct
mode = ChangeDetectionMode.GIT_DIFF  # or "git_diff"

# Incorrect - will raise ValueError
mode = "git-diff"  # Wrong: hyphen instead of underscore
```

The validator provides helpful error messages:

```text
ValueError: Invalid mode: 'git-diff'. Did you mean 'git_diff'?
Valid modes: 'checksum', 'git_diff'
```

### Choosing between modes

**Use Checksum if**:
- You have established baselines with `docmgr_init`
- You want to track all file changes (including untracked)
- You're not using git or don't want git dependency
- You want to reset baseline knowledge

**Use Git Diff if**:
- You're in CI/CD pipeline comparing against base commit
- You want to detect changes relative to specific commit
- You want to avoid baseline file management
- You're comparing PR branches

---

## Constants

Related constants available in `doc_manager_mcp.constants`:

### Resource limits

```python
MAX_FILES = 10_000          # Maximum files to process per operation
MAX_RECURSION_DEPTH = 100   # Maximum symlink resolution depth
OPERATION_TIMEOUT = 60      # Operation timeout in seconds
CHARACTER_LIMIT = 25000     # Maximum response size in characters
```

### Quality assessment

```python
QUALITY_CRITERIA = [
    "relevance",
    "accuracy",
    "purposefulness",
    "uniqueness",
    "consistency",
    "clarity",
    "structure"
]
```

### Supported platforms

```python
SUPPORTED_PLATFORMS = [
    "hugo",
    "docusaurus",
    "mkdocs",
    "sphinx",
    "vitepress",
    "jekyll",
    "gitbook"
]
```

### Default directories

```python
DOC_DIRECTORIES = [
    "docsite",
    "docs",
    "documentation",
    "website",
    "site"
]
```

---

## Usage patterns

### Type-safe enum usage

```python
from doc_manager_mcp.constants import DocumentationPlatform, ChangeDetectionMode

# Type-safe - IDE will autocomplete
platform: DocumentationPlatform = DocumentationPlatform.MKDOCS
mode: ChangeDetectionMode = ChangeDetectionMode.CHECKSUM

# From string (with error handling)
try:
    platform = DocumentationPlatform(user_input)
except ValueError as e:
    print(f"Invalid platform: {e}")
```

### Iterating enums

```python
from doc_manager_mcp.constants import DocumentationPlatform, QualityCriterion

# All platforms except unknown
for platform in DocumentationPlatform:
    if platform != DocumentationPlatform.UNKNOWN:
        print(f"{platform.value}: {platform.name}")

# All quality criteria
from doc_manager_mcp.constants import QUALITY_CRITERIA

for criterion in QUALITY_CRITERIA:
    print(f"Criterion: {criterion}")
```

### String conversion

```python
from doc_manager_mcp.constants import DocumentationPlatform

platform = DocumentationPlatform.SPHINX

# Get string value
value = platform.value          # "sphinx"
name = platform.name            # "SPHINX"

# Comparison
if platform.value == "sphinx":
    print("Python-friendly!")
```

---

## See also

- [Models reference](./models.md) - Input/output model schemas
- [Configuration reference](../configuration.md) - Configuration file schemas
- [Tools reference](../tools.md) - Tool descriptions and usage
