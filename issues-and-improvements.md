# Doc-Manager: Issues and Improvements

**Test Project**: pass-cli (Hugo-based documentation)
**Test Date**: 2025-11-17
**Purpose**: Identify limitations and improvement opportunities for doc-manager MCP server

---

## Executive Summary

Testing revealed doc-manager works well for standard markdown projects but has significant limitations with Hugo-based documentation. Key findings:
- **3/7 quality assessment criteria** produced false positives
- **Validation** cannot handle Hugo shortcodes or content resolution
- **Dependency tracking** only captures literal file references, not semantic relationships
- **Map changes** has unclear mode parameters

**Overall**: Tool needs Hugo-awareness improvements and better markdown parsing to reduce false positives.

---

## 1. Validation Issues

### 1.1 Hugo Shortcode Handling

**Issue**: Cannot resolve Hugo `{{< relref >}}` shortcodes

**Example**:
```markdown
[Quick Install]({{< relref "01-getting-started/quick-install" >}})
```

**What happens**:
- File `01-getting-started/quick-install.md` exists
- Tool reports link as broken
- Hugo processes shortcode correctly when building site

**Impact**: High - Reports 45+ false positives for Hugo projects

**Root cause**: Tool validates raw markdown before Hugo processing

---

### 1.2 Path Resolution

**Issue**: Expects filesystem paths with `.md` extension; Hugo uses content paths without extension

**Example**:
- doc-manager expects: `01-getting-started/quick-install.md`
- Hugo uses: `01-getting-started/quick-install`
- Both are valid in their contexts

**What happens**:
- Standard markdown links without `.md` work in Hugo
- Tool cannot validate these as it checks filesystem
- Results in "target not found" errors

**Impact**: High - 52 broken link reports, most are false positives

**Root cause**: Not "Hugo-aware" - doesn't understand Hugo's content resolution

---

## 2. Quality Assessment Issues

### 2.1 Deprecated References (False Positive)

**Issue**: Counts documentation ABOUT deprecations as deprecated content

**Reported**: 59 deprecated references across 11 files

**Example findings**:
```markdown
migration.md: "The `--vault` flag has been removed"
homebrew.md: "Don't use deprecated Homebrew DSL features"
```

**Reality**: These are:
- ✓ Useful migration documentation
- ✓ Historical context for users
- ✓ Guidance about deprecated external features

**Impact**: Medium - Misleading quality score

**Root cause**: Simple keyword matching ("deprecated", "removed", "no longer") without context understanding

---

### 2.2 Duplicate Headers (False Positive)

**Issue**: Parses code comments inside fenced code blocks as markdown headers

**Reported**: 77 duplicate headers

**Example**:
````markdown
```bash
# Extract expected checksum  ← Counted as header!
# Calculate actual checksum
# Compare
```
````

**Reality**:
- Code comments in bash/PowerShell blocks
- Platform-specific parallel structure (macOS/Linux vs Windows)
- Improves documentation clarity

**Impact**: Medium - Inflates duplicate count

**Root cause**: Header detection doesn't exclude content inside code fences

---

### 2.3 Heading Hierarchy (Unclear)

**Issue**: Reports 27 files with heading hierarchy issues (e.g., H2 → H4 skipping H3)

**Sample check**: `command-reference.md` showed proper hierarchy:
```
H2: Global Options
  H3: Global Flag Examples
  H3: Custom Vault Location
H2: Commands
  H3: init - Initialize Vault
    H4: Synopsis
```

**Reality**: Unable to confirm actual issues exist

**Impact**: Low-Medium - May be false positive

**Root cause**: Unknown - couldn't verify actual problems

---

### 2.4 Code Block Language Tags (Unclear)

**Issue**: Reports 577 code blocks missing language tags

**User question**: "Aren't opening fences `\`\`\`bash` and closing just `\`\`\``?"

**Investigation**:
- Could not find code blocks without language tags
- Tool may be incorrectly counting closing fences
- Or detecting edge cases we didn't find

**Impact**: Unknown - Needs investigation

**Root cause**: Possible bug in language tag detection

---

## 3. Dependency Tracking Limitations

### 3.1 Literal References Only

**Issue**: Only tracks when docs explicitly mention file paths

**Example**:
- `command-reference.md` documents 26 commands
- Only references 6 `.go` files explicitly
- Other 20 commands documented but no file dependency tracked

**Impact**: High - Incomplete dependency graph

**What's tracked**:
- ✓ Explicit file paths: `cmd/add.go`
- ✓ Command names: "pass-cli add", "generate"
- ✓ Config keys: "vault_path", "username"

**What's missing**:
- ✗ Semantic links: "add command" → `cmd/add.go`
- ✗ Inferred relationships

---

### 3.2 Dependency Mapping Results

**Overall**: 272 references, 26 doc files, 124 source files

**Actual file dependencies**:
- Only 10/26 `cmd/*.go` files tracked
- Missing: `change_password.go`, `generate.go`, `keychain*.go`, `vault*.go`, etc.

**Command references** (separate tracking):
- "change-password" → documented in 1 file
- "pass-cli change-password --recover" → documented in 4 files

**Gap**: Commands are tracked, but not linked to implementing source files

**Impact**: Medium - Limits usefulness for "code change → affected docs" workflow

---

## 4. Map Changes Issues

### 4.1 Mode Parameter Unclear

**Issue**: Only "checksum" mode works; git diff modes fail

**Attempted modes**:
- ✓ `mode: "checksum"` - Works
- ✓ (no mode parameter) - Defaults to checksum, works
- ✗ `mode: "git"` - Error: not a valid ChangeDetectionMode
- ✗ `mode: "diff"` - Error: not a valid ChangeDetectionMode
- ✗ `mode: "git-diff"` - Error: not a valid ChangeDetectionMode

**Impact**: Medium - Limits functionality, unclear if git diff is implemented

---

### 4.2 Commit Hash Validation

**Issue**: `since_commit` requires actual SHA hash, not git refs

**Example**:
- ✗ `since_commit: "HEAD~3"` - Validation error
- ✓ `since_commit: "2270ea1"` - Works

**Reason**: Security - prevents command injection attacks

**Impact**: Low - Good security practice, but requires extra step to get SHA

---

## 5. Tool Applicability

### 5.1 Works Well For

**Standard Markdown Projects**:
- ✓ GitHub-rendered documentation
- ✓ Generic markdown renderers
- ✓ Projects without static site generators

**Features that work well**:
- ✓ Asset/image validation
- ✓ Dependency tracking (literal references)
- ✓ Sync dashboard (combines all tools)

---

### 5.2 Limited For

**Hugo / Static Site Generators**:
- ✗ Custom shortcodes
- ✗ Content path resolution
- ✗ Build-time transformations

**Recommendation for Hugo projects**:
- Use Hugo render hooks for link validation (build-time)
- Use existing CI workflows (`docs-validation.yml`)
- Use doc-manager for: asset checks, quality insights, dependency tracking

---

## 6. Positive Findings

### 6.1 Sync Tool

**Purpose**: Documentation health dashboard

**Combines**:
- Change detection (`map_changes`)
- Validation (`validate_docs`)
- Quality assessment (`assess_quality`)
- Dependency data (`track_dependencies`)

**Output**: Single comprehensive report with actionable recommendations

**Value**: High - Good for periodic documentation health checks

---

### 6.2 Quality Assessment (When Accurate)

**Strong points identified**:
- ✓ Accuracy: 410 code blocks, diverse languages
- ✓ Clarity: 30/38 files have examples, good cross-referencing

**Useful metrics**:
- Code block language diversity
- Example coverage
- Cross-reference tracking

---

## 7. Recommended Improvements

### Priority 1: Critical

1. **Hugo shortcode support**
   - Detect Hugo projects (`hugo.yaml`/`config.toml`)
   - Skip shortcode validation or resolve common patterns
   - Add Hugo-specific validation mode

2. **Fix code fence parsing**
   - Exclude content inside `\`\`\`` blocks from header detection
   - Prevents false positives for duplicate headers

3. **Improve deprecated detection**
   - Context-aware analysis
   - Distinguish "docs ABOUT deprecations" vs "deprecated docs"
   - Consider semantic analysis

---

### Priority 2: Important

4. **Dependency tracking enhancements**
   - Semantic relationship detection
   - Language-specific parsing (match command docs → implementation)
   - Configuration for custom mappings

5. **Path resolution improvements**
   - Hugo content path support (without `.md`)
   - Static site generator awareness
   - Configurable path validation rules

6. **Map changes clarity**
   - Document valid mode values
   - Implement git diff mode (if planned)
   - Better error messages for mode parameter

---

### Priority 3: Nice-to-Have

7. **Quality assessment refinements**
   - Investigate code block language tag detection
   - Verify heading hierarchy detection
   - Add confidence scores to findings

8. **Documentation**
   - Clear mode parameter documentation
   - Hugo-specific usage guide
   - False positive troubleshooting guide

---

## 8. Test Results Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Validation (Standard MD) | ✓ Good | Works for non-Hugo projects |
| Validation (Hugo) | ✗ Limited | Many false positives |
| Quality: Deprecated Refs | ✗ False Positive | Needs context awareness |
| Quality: Duplicate Headers | ✗ False Positive | Parses code comments |
| Quality: Heading Hierarchy | ⚠️ Unclear | Couldn't verify issues |
| Quality: Code Block Tags | ⚠️ Unclear | Needs investigation |
| Quality: Accuracy/Clarity | ✓ Good | Useful metrics |
| Dependency Tracking | ⚠️ Partial | Literal refs only |
| Map Changes | ⚠️ Limited | Only checksum mode |
| Sync Dashboard | ✓ Good | Useful overview |

---

## Appendix: Example Hugo Render Hook Solution

**Problem**: doc-manager can't validate Hugo links

**User's solution**: Created Hugo render hook for build-time validation

```html
<!-- docsite/layouts/_default/_markup/render-link.html -->
{{- $url := urls.Parse .Destination -}}
{{- if $url.Scheme -}}
  {{/* External link */}}
  <a href="{{ .Destination | safeURL }}">{{ .Text | safeHTML }}</a>
{{- else -}}
  {{- with $.Page.GetPage $url.Path -}}
    {{/* Valid internal link */}}
    <a href="{{ .RelPermalink }}">{{ $.Text | safeHTML }}</a>
  {{- else -}}
    {{/* Broken link - fail build */}}
    {{- errorf "Broken internal link in %s: target '%s' not found" $.Page.File.Path $url.Path -}}
  {{- end -}}
{{- end -}}
```

**Benefits**:
- Validates at Hugo build time
- Understands Hugo content resolution
- Fails CI on broken links
- Works with standard markdown (no `.md` extension needed)

**Outcome**: User now has both:
- Hugo render hook (Hugo-specific validation)
- doc-manager (cross-platform insights, quality metrics)

---

## 9. Phase 2 Architecture: Production-Ready Dependency Tracking

**Context**: Current regex-based dependency tracking works for pass-cli but lacks robustness for general-purpose use across different projects, languages, and conventions.

**Goal**: Build a solid foundation that works with ANY project and genuinely helps with documentation creation and maintenance.

### 9.1 Architecture Decision

Based on analysis and consultation with Gemini, implementing a **three-layer architecture**:

1. **Code Indexing (TreeSitter)** - Accurate symbol extraction via AST parsing
2. **Doc Parsing (Enhanced Regex)** - Fast reference extraction from markdown
3. **Linking (Configurable Mappings)** - User-defined semantic mappings

### 9.2 Layer 1: Code Indexing with TreeSitter

**Purpose**: Build accurate "ground truth" of what code symbols exist

**Implementation**:
- Use `py-tree-sitter` with language-specific parsers
- Parse source files to extract AST definitions
- Build in-memory symbol index

**Example symbol index**:
```python
{
  "SaveVault": {
    "file": "internal/vault/vault.go",
    "line": 42,
    "type": "function",
    "signature": "func SaveVault(vault *Vault, path string) error"
  },
  "Config": {
    "file": "internal/config/config.go",
    "line": 15,
    "type": "struct",
    "fields": ["VaultPath", "KeychainEnabled"]
  }
}
```

**Languages to support**:
- Go (priority 1 - pass-cli)
- Python (priority 1 - common)
- JavaScript/TypeScript (priority 1 - common)
- Rust (priority 2)
- Java (priority 2)

**Benefits**:
- ✓ 100% accurate symbol detection
- ✓ No false positives from text search
- ✓ Deterministic and fast (C-based parser)
- ✓ Language-aware (understands imports, namespaces)

**Tradeoffs**:
- Initial setup: language parser dependencies
- Maintenance: keep parsers updated

---

### 9.3 Layer 2: Enhanced Doc Parsing

**Purpose**: Extract references from markdown documentation

**Current patterns** (keep and enhance):
- Literal file paths: `` `cmd/add.go` ``
- Function references: `` `SaveVault()` ``
- Semantic commands: "add command", "the generate subcommand"
- Config keys: `` `vault_path` ``

**Enhancements**:
- Better phrase extraction patterns
- Multi-word command detection
- Nested namespace handling (e.g., `vault.Config.Load()`)

**Keep regex because**:
- ✓ Blazing fast for text scanning
- ✓ Perfect for literal/structured patterns
- ✓ No external dependencies for core logic
- ✓ Handles 80% of common cases

---

### 9.4 Layer 3: Configurable Mappings

**Purpose**: Bridge semantic phrases to code paths using project conventions

**Configuration file**: `.doc-manager.yml`

**Example mappings**:
```yaml
# Project-specific semantic mappings
semantic_mappings:
  # CLI commands (Go/Cobra pattern)
  - pattern: 'the (.*) command'
    template: 'cmd/{name}.go'
    language: go

  - pattern: '`(.*)` subcommand'
    template: 'cmd/{name}.go'
    language: go

  # Django views (Python pattern)
  - pattern: 'the (.*) view'
    template: 'views/{name}.py'
    language: python

  # Express routes (Node.js pattern)
  - pattern: '(.*) endpoint'
    template: 'routes/{name}.js'
    language: javascript

  # API handlers
  - pattern: '(.*) handler'
    template: 'handlers/{name}.go'
    language: go

# Symbols to ignore during analysis
ignore_symbols:
  - 'main'
  - 'init'
  - 'test'

# Custom file path patterns
file_patterns:
  - 'internal/**/*.go'
  - 'pkg/**/*.go'
  - 'src/**/*.{py,js,ts}'
```

**Validation**:
- Extracted references → Match against mappings → Validate against TreeSitter index
- Only report matches that exist in the codebase
- Flag references that don't match any known symbols

**Benefits**:
- ✓ Adapts to any project structure
- ✓ User-controlled without code changes
- ✓ Explicit and deterministic
- ✓ Can handle project-specific conventions

---

### 9.5 Implementation Phases

**Phase 2.1: TreeSitter Integration**
- [ ] Add `py-tree-sitter` dependency
- [ ] Create `src/indexing/tree_sitter.py` module
- [ ] Implement Go parser integration
- [ ] Implement Python parser integration
- [ ] Implement JavaScript/TypeScript parser integration
- [ ] Build symbol index data structure
- [ ] Add caching for performance
- [ ] Unit tests for each language

**Phase 2.2: Configurable Mappings**
- [ ] Extend `.doc-manager.yml` schema
- [ ] Add `semantic_mappings` configuration
- [ ] Parse and validate mapping rules
- [ ] Apply mappings during dependency linking
- [ ] Add validation against symbol index
- [ ] Documentation and examples
- [ ] Integration tests

**Phase 2.3: Enhanced Dependency Tracking**
- [ ] Update `track_dependencies` to use symbol index
- [ ] Match extracted references against index
- [ ] Apply configurable mappings
- [ ] Improve reverse index accuracy
- [ ] Add confidence scores to matches
- [ ] Performance optimization

**Phase 2.4: Multi-Project Testing**
- [ ] Test on pass-cli (Go/Cobra)
- [ ] Test on Python project (Django/Flask)
- [ ] Test on Node.js project (Express)
- [ ] Document best practices per framework
- [ ] Create example `.doc-manager.yml` files

---

### 9.6 Success Criteria

**Accuracy**:
- ✓ Zero false positives from text search
- ✓ Matches only actual code symbols that exist
- ✓ Handles multi-language projects

**Usability**:
- ✓ Works out-of-box for common frameworks
- ✓ Easy to configure for custom projects
- ✓ Clear error messages when references don't match

**Performance**:
- ✓ Indexing completes in <5s for medium projects (10K LOC)
- ✓ Dependency tracking in <10s for 100+ doc files
- ✓ Incremental updates for file changes

**Maintainability**:
- ✓ Adding new language support is straightforward
- ✓ Users can extend without modifying code
- ✓ Clear separation of concerns (indexing/parsing/linking)

---

### 9.7 Why Not spaCy or Vector Databases?

**spaCy verdict**: NOT recommended
- 100MB model overhead not justified
- Slower than regex for simple phrase extraction
- Regex + configurable mappings handle this well enough
- Could add later as "v2 feature" if needed

**Vector DB verdict**: Strongly NOT recommended
- Too heavy (hundreds of MBs)
- Non-deterministic results
- Slow (embedding generation + search)
- Wrong tool for structured code references
- Better suited for fuzzy semantic search, not dependency tracking

**Chosen approach**: Start with deterministic, lightweight solution (TreeSitter + regex + config). Add advanced NLP only if proven insufficient.
