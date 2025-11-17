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
