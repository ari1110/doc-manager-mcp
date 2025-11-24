# Optimization Roadmap - Prioritized Improvements

## Executive Summary

This document provides a prioritized, actionable roadmap for improving doc-manager based on comprehensive tracing of 6 tools (75% coverage). Improvements are organized by priority, effort, and impact.

**Quick Stats:**
- **2 CRITICAL** issues (file locking, hardcoded paths)
- **7 HIGH priority** optimizations (performance + complexity)
- **5 MEDIUM priority** improvements (code quality)
- **3 LOW priority** enhancements (polish)

**Total effort estimate:** 40-60 hours to implement all improvements
**Expected impact:** 70-75% performance improvement, 2-point code quality increase

---

## Priority Framework

Issues and improvements are prioritized using this framework:

**CRITICAL (P0)** - Must fix immediately
- Data corruption risk
- Correctness issues that affect output accuracy
- Security vulnerabilities
- **Effort:** Varies
- **Timeline:** Within 1 week

**HIGH (P1)** - Should fix soon
- Major performance bottlenecks (>2x improvement)
- Significant complexity reduction
- Maintainability issues in frequently changed code
- **Effort:** 2-6 hours each
- **Timeline:** Within 1 month

**MEDIUM (P2)** - Nice to have
- Moderate performance improvements
- Code quality enhancements
- Reduced duplication
- **Effort:** 1-3 hours each
- **Timeline:** Within 3 months

**LOW (P3)** - Optional polish
- Minor improvements
- Edge case handling
- Configuration flexibility
- **Effort:** 1-2 hours each
- **Timeline:** Backlog / as time permits

---

## CRITICAL Priority (P0) - Fix Immediately

### 1. Add File Locking to update_baseline
**Tool:** docmgr_update_baseline
**Issue:** Race conditions can corrupt baseline files
**Risk Level:** HIGH - Data corruption possible

**Problem:**
```python
# doc_manager_mcp/tools/state/update_baseline.py:196
# NO FILE LOCKING - Multiple processes can write simultaneously
baseline_path.write_text(json.dumps(baseline, indent=2))
```

When multiple processes run `update_baseline` concurrently (e.g., in CI/CD), they can corrupt baseline files by writing partial data.

**Solution:**
Add file locking with `filelock` library:

```python
# Install: pip install filelock
from filelock import FileLock

def _update_repo_baseline(project_path, ...):
    baseline_path = project_path / ".doc-manager" / "repo-baseline.json"
    lock_path = baseline_path.with_suffix(".lock")

    # Acquire lock before writing
    with FileLock(lock_path, timeout=10):
        # ... build baseline ...
        baseline_path.write_text(json.dumps(baseline, indent=2))
```

Apply same pattern to:
- Line 196: repo-baseline.json write
- Line 232: symbol-baseline.json write
- Line 268: dependencies.json write

**Effort:** 30 minutes
**Impact:** Prevents data corruption in concurrent scenarios
**Timeline:** Immediate (this week)

**Implementation Steps:**
1. Add `filelock>=3.0.0` to pyproject.toml dependencies
2. Create `core/file_utils.py` with `safe_write_json()` helper:
   ```python
   from filelock import FileLock
   import json

   def safe_write_json(path: Path, data: dict, timeout=10):
       lock_path = path.with_suffix(path.suffix + ".lock")
       with FileLock(lock_path, timeout=timeout):
           path.write_text(json.dumps(data, indent=2))
   ```
3. Replace all `baseline_path.write_text(...)` calls with `safe_write_json(...)`
4. Add test: Run 5 concurrent `update_baseline` calls, verify no corruption
5. Document in CHANGELOG.md

---

### 2. Make Doc Paths Configurable in detect_changes
**Tool:** docmgr_detect_changes
**Issue:** Hardcoded doc paths cause inaccurate results for non-standard layouts
**Risk Level:** HIGH - Correctness issue

**Problem:**
```python
# doc_manager_mcp/tools/_internal/changes.py:260-339
# 9 HARDCODED doc paths - fails for non-standard layouts
if category == "cli":
    _add_affected_doc(
        affected_docs,
        "docs/reference/command-reference.md",  # ❌ Hardcoded
        ...
    )
```

Projects with different layouts (e.g., `documentation/`, `wiki/`, `_docs/`) get incorrect affected doc mappings.

**Solution:**
Add `doc_paths` configuration to `.doc-manager.yml`:

```yaml
# .doc-manager.yml
doc_paths:
  cli: "docs/reference/command-reference.md"
  core: "docs/architecture/core-architecture.md"
  dependencies: "docs/reference/dependency-tracking.md"
  validation: "docs/reference/validation.md"
  quality: "docs/reference/quality-assessment.md"
  mcp: "docs/reference/mcp-server.md"
  config: "docs/configuration/settings.md"
  platform: "docs/setup/platform-detection.md"
  state: "docs/architecture/state-management.md"
```

Then load in code:
```python
def _map_to_affected_docs(changed_files, category, project_path):
    config = load_config(project_path)
    doc_paths = config.get("doc_paths", {})

    # Use configured path, fallback to default
    doc_path = doc_paths.get(category, f"docs/reference/{category}.md")

    if doc_path and (project_path / doc_path).exists():
        _add_affected_doc(affected_docs, doc_path, ...)
```

**Effort:** 4-6 hours
**Impact:** Fixes correctness for all project layouts
**Timeline:** This week

**Implementation Steps:**
1. Update `core/config.py` schema to include `doc_paths: Dict[str, str]`
2. Update `docmgr_init` to optionally generate default `doc_paths` mapping
3. Refactor `_map_to_affected_docs()` to use config (changes.py:260-339)
4. Add tests for non-standard layouts
5. Update documentation: `docs/configuration/settings.md`
6. Provide migration guide for existing projects

---

## HIGH Priority (P1) - Fix Within 1 Month

### 3. Build Link Index for validate_docs
**Tool:** docmgr_validate_docs
**Issue:** Quadratic complexity O(M×L×M) in link validation
**Performance Impact:** 5-10x faster link validation

**Current Complexity:**
```python
# O(M×L×M) - QUADRATIC
for md_file in markdown_files:              # M iterations
    for link in extract_links(md_file):     # L iterations
        for target_file in markdown_files:  # M iterations - BAD!
            if resolve_link(link, target_file):
                break
```

**Optimized Approach:**
```python
# Build index once: O(M)
def build_link_index(markdown_files):
    index = {}
    for md_file in markdown_files:
        # Index all possible link targets
        index[md_file.stem] = md_file
        index[str(md_file.relative_to(docs_path))] = md_file
        index[md_file.name] = md_file
    return index

# Query in O(1)
link_index = build_link_index(markdown_files)

# O(M×L) - LINEAR
for md_file in markdown_files:              # M iterations
    for link in extract_links(md_file):     # L iterations
        target = link_index.get(normalize_link(link))  # O(1) lookup!
        if not target:
            issues.append(f"Broken link: {link}")
```

**Effort:** 2-3 hours
**Impact:** validate_docs 3-5x faster overall
**Timeline:** Week 1-2

**Implementation Steps:**
1. Create `indexing/link_index.py` with `build_link_index()` function
2. Update `_check_broken_links()` to use index (validator.py:109-149)
3. Handle edge cases: extensionless links, anchors, relative paths
4. Add benchmarks to verify speedup
5. Update architecture diagram: `validate_docs_arch/link-validation.mmd`

---

### 4. Cache Markdown Parsing (validate_docs + assess_quality)
**Tools:** docmgr_validate_docs, docmgr_assess_quality
**Issue:** Each tool parses files multiple times
**Performance Impact:** 30-50% faster for both tools

**Current Waste:**
- validate_docs: Parses each file up to 6 times (once per validator)
- assess_quality: Parses each file 7 times (once per criterion)
- When both run (e.g., in sync): Parse each file 13 times total

**Solution:**
```python
# core/markdown_cache.py
from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path

@dataclass
class ParsedMarkdown:
    headings: List[tuple]  # (level, text)
    links: List[str]
    images: List[tuple]    # (alt, src)
    code_blocks: List[tuple]  # (language, code)
    ast: Any               # Full markdown AST

class MarkdownCache:
    def __init__(self):
        self._cache: Dict[Path, ParsedMarkdown] = {}

    def parse(self, file_path: Path, content: str) -> ParsedMarkdown:
        if file_path not in self._cache:
            parser = MarkdownParser(content)
            self._cache[file_path] = ParsedMarkdown(
                headings=parser.extract_headings(),
                links=parser.extract_links(),
                images=parser.extract_images(),
                code_blocks=parser.extract_code_blocks(),
                ast=parser.parse_ast()
            )
        return self._cache[file_path]

    def clear(self):
        self._cache.clear()
```

Usage:
```python
# Pass cache to both tools
cache = MarkdownCache()
validate_results = validate_docs(..., markdown_cache=cache)
quality_results = assess_quality(..., markdown_cache=cache)
```

**Effort:** 2-3 hours
**Impact:**
- validate_docs: 30-40% faster
- assess_quality: 40-50% faster
- Combined (sync): 35-45% faster

**Timeline:** Week 1-2

**Implementation Steps:**
1. Create `core/markdown_cache.py` with `MarkdownCache` class
2. Update `validate_docs()` signature to accept optional cache parameter
3. Update `assess_quality()` signature to accept optional cache parameter
4. Update all internal parsing calls to use cache
5. Add cache clearing for watch mode / long-running processes
6. Add benchmarks

---

### 5. Extract Shared File Scanning Logic
**Tools:** docmgr_init, docmgr_update_baseline, docmgr_detect_changes
**Issue:** Duplicate file scanning code in 3 tools
**Impact:** Reduces duplication, enables shared caching

**Current Duplication:**
- init.py:~80-120 - File scanning logic
- update_baseline.py:~110-160 - Nearly identical
- changes.py:~180-220 - Similar with minor variations

**Solution:**
Extract to `core/patterns.py`:

```python
# core/patterns.py
from pathlib import Path
from typing import List, Set
import os

def scan_project_files(
    project_path: Path,
    exclude_patterns: List[str],
    sources: Optional[List[str]] = None,
    include_hidden: bool = False
) -> Dict[str, List[Path]]:
    """
    Scan project files and categorize them.

    Returns:
        {
            "code": [Path(...), ...],
            "docs": [Path(...), ...],
            "assets": [Path(...), ...],
            "config": [Path(...), ...]
        }
    """
    categorized = {"code": [], "docs": [], "assets": [], "config": []}

    for root, dirs, files in os.walk(project_path):
        # Filter directories
        dirs[:] = [d for d in dirs if not _should_exclude(d, exclude_patterns)]

        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(project_path)

            if _should_exclude(str(rel_path), exclude_patterns):
                continue

            # Categorize file
            category = _categorize_file(file_path)
            categorized[category].append(rel_path)

    return categorized

def _categorize_file(file_path: Path) -> str:
    """Categorize file by extension and location."""
    suffix = file_path.suffix.lower()

    # Code files
    if suffix in {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c"}:
        return "code"

    # Documentation
    if suffix in {".md", ".rst", ".txt"}:
        return "docs"

    # Assets
    if suffix in {".png", ".jpg", ".svg", ".gif", ".pdf"}:
        return "assets"

    # Config
    if suffix in {".yml", ".yaml", ".toml", ".json", ".ini"}:
        return "config"

    return "other"

def _should_exclude(path: str, patterns: List[str]) -> bool:
    """Check if path matches exclude patterns."""
    # Implementation with fnmatch or regex
    ...
```

**Effort:** 2-3 hours
**Impact:** Removes ~120 lines of duplication, enables shared caching
**Timeline:** Week 2

**Implementation Steps:**
1. Create `core/patterns.py` with `scan_project_files()`, `_categorize_file()`, `_should_exclude()`
2. Update init.py to use shared function
3. Update update_baseline.py to use shared function
4. Update changes.py to use shared function
5. Add comprehensive tests for categorization logic
6. Remove old duplicate code

---

### 6. Extract Shared Exclude Pattern Building
**Tools:** docmgr_init, docmgr_update_baseline, docmgr_detect_changes
**Issue:** Duplicate exclude pattern logic in 3 tools
**Impact:** Consistent behavior across tools

**Current Duplication:**
- All 3 tools have nearly identical `build_exclude_patterns()` logic
- Gitignore parsing duplicated
- Default patterns scattered

**Solution:**
Add to `core/patterns.py`:

```python
# core/patterns.py (continued)
def build_exclude_patterns(
    project_path: Path,
    use_gitignore: bool = False,
    custom_patterns: Optional[List[str]] = None
) -> List[str]:
    """
    Build exclude patterns from gitignore + custom patterns.

    Returns:
        List of glob patterns to exclude
    """
    patterns = []

    # Default excludes
    patterns.extend([
        "**/.git/**",
        "**/__pycache__/**",
        "**/node_modules/**",
        "**/.venv/**",
        "**/venv/**",
        "**/.doc-manager/**",
    ])

    # Parse .gitignore
    if use_gitignore:
        gitignore_path = project_path / ".gitignore"
        if gitignore_path.exists():
            patterns.extend(_parse_gitignore(gitignore_path))

    # Add custom patterns
    if custom_patterns:
        patterns.extend(custom_patterns)

    return patterns

def _parse_gitignore(gitignore_path: Path) -> List[str]:
    """Parse .gitignore file into glob patterns."""
    patterns = []
    for line in gitignore_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # Convert gitignore syntax to glob
            pattern = _gitignore_to_glob(line)
            patterns.append(pattern)
    return patterns
```

**Effort:** 1-2 hours
**Impact:** Removes ~60 lines of duplication, ensures consistency
**Timeline:** Week 2

---

### 7. Modularize validate_docs (Extract 6 Validators)
**Tool:** docmgr_validate_docs
**Issue:** 573 lines in single file, violates Single Responsibility Principle
**Impact:** Reduces complexity from 5→3, improves maintainability

**Current Structure:**
```
validation/
└── validator.py  [573 lines] - Everything in one file
```

**Target Structure:**
```
validation/
├── validator.py          [100 lines] - Main orchestrator + shared utils
├── conventions.py        [80 lines] - Convention validation
├── links.py              [100 lines] - Link validation + index
├── assets.py             [100 lines] - Asset validation
├── snippets.py           [80 lines] - Code snippet validation
├── syntax.py             [60 lines] - Deep syntax validation
└── symbols.py            [80 lines] - Symbol validation
```

**Orchestrator Pattern:**
```python
# validation/validator.py [100 lines]
from .conventions import validate_conventions
from .links import validate_links
from .assets import validate_assets
from .snippets import validate_snippets
from .syntax import validate_syntax
from .symbols import validate_symbols

def validate_docs(
    docs_path: Path,
    check_links: bool = True,
    check_assets: bool = True,
    check_snippets: bool = True,
    validate_code_syntax: bool = False,
    validate_symbols: bool = False,
    markdown_cache: Optional[MarkdownCache] = None
) -> dict:
    """Orchestrate 6 validators."""
    issues = []
    md_files = find_markdown_files(docs_path)

    # Run validators conditionally
    if check_links:
        issues.extend(validate_links(md_files, docs_path, markdown_cache))

    if check_assets:
        issues.extend(validate_assets(md_files, docs_path, markdown_cache))

    # ... other validators ...

    return aggregate_issues(issues)
```

**Effort:** 3-4 hours
**Impact:** Complexity 5→3, much easier to maintain/test
**Timeline:** Week 3

---

### 8. Modularize assess_quality (Extract 7 Analyzers)
**Tool:** docmgr_assess_quality
**Issue:** 771 lines in single file, 2nd largest tool
**Impact:** Reduces complexity from 5→3

**Current Structure:**
```
quality/
└── assessment.py  [771 lines] - Everything in one file
```

**Target Structure:**
```
quality/
├── assessment.py         [150 lines] - Main orchestrator
├── relevance.py          [100 lines] - Relevance analyzer
├── accuracy.py           [120 lines] - Accuracy analyzer
├── purposefulness.py     [90 lines] - Purposefulness analyzer
├── uniqueness.py         [120 lines] - Uniqueness analyzer
├── consistency.py        [130 lines] - Consistency analyzer
├── clarity.py            [110 lines] - Clarity analyzer
└── structure.py          [100 lines] - Structure analyzer
```

**Effort:** 3-4 hours
**Impact:** Complexity 5→3, easier to tune heuristics
**Timeline:** Week 3

---

### 9. Path Index for detect_changes (Like dependency tracking)
**Tool:** docmgr_detect_changes
**Issue:** Slow affected doc mapping
**Performance Impact:** 2-3x faster affected doc mapping

**Solution:**
Apply same optimization used for dependency tracking:

```python
# Build path index once
def build_path_index(project_path, sources):
    index = {
        "by_category": {},  # {category: [files]}
        "by_name": {},      # {filename: full_path}
        "by_pattern": {}    # {pattern: [files]}
    }

    for file_path in scan_project_files(project_path, sources):
        category = categorize_file(file_path)
        index["by_category"].setdefault(category, []).append(file_path)
        index["by_name"][file_path.name] = file_path

    return index

# Use index for O(1) lookups
def map_to_affected_docs(changed_files, config, path_index):
    affected_docs = []

    for file in changed_files:
        category = file["category"]

        # O(1) lookup in config
        doc_path = config["doc_paths"].get(category)
        if doc_path:
            affected_docs.append(doc_path)

    return affected_docs
```

**Effort:** 2-3 hours
**Impact:** 2-3x faster for projects with many files
**Timeline:** Week 2-3

---

## MEDIUM Priority (P2) - Fix Within 3 Months

### 10. Parallelize Validators (validate_docs)
**Tool:** docmgr_validate_docs
**Performance Impact:** 2-3x faster

**Solution:**
```python
import asyncio

async def validate_docs_async(...):
    validators = [
        validate_conventions_async(...),
        validate_links_async(...),
        validate_assets_async(...),
        validate_snippets_async(...),
        validate_syntax_async(...),
        validate_symbols_async(...)
    ]

    results = await asyncio.gather(*validators)
    return aggregate_results(results)
```

**Effort:** 2 hours (after modularization)
**Timeline:** Month 2

---

### 11. Parallelize Analyzers (assess_quality)
**Tool:** docmgr_assess_quality
**Performance Impact:** 2-3x faster

Similar to #10, run 7 analyzers concurrently.

**Effort:** 2 hours (after modularization)
**Timeline:** Month 2

---

### 12. Split `_update_repo_baseline()` Function
**Tool:** docmgr_update_baseline
**Issue:** 109-line function with 5 responsibilities
**Impact:** Improves readability

**Solution:**
```python
def _update_repo_baseline(project_path, ...):
    exclude = _build_exclude_patterns(...)
    files = _scan_project_files(project_path, exclude)
    baseline = _build_baseline_structure(files)
    _calculate_checksums(baseline)
    _write_baseline_safely(baseline_path, baseline)
```

**Effort:** 2 hours
**Timeline:** Month 2

---

### 13. Extract Categorization Patterns (detect_changes)
**Tool:** docmgr_detect_changes
**Issue:** 15+ hardcoded patterns in `_categorize_changed_file()`
**Impact:** Easier to extend

**Solution:**
Move patterns to `core/patterns.py`:

```python
FILE_CATEGORY_PATTERNS = {
    "cli": ["**/cli/**", "**/cmd/**", "**/commands/**"],
    "core": ["**/core/**", "**/lib/**", "**/src/**"],
    "validation": ["**/validation/**", "**/validators/**"],
    # ... configurable patterns
}
```

**Effort:** 2-3 hours
**Timeline:** Month 2

---

### 14. Incremental Validation (Only Changed Docs)
**Tool:** docmgr_validate_docs
**Performance Impact:** 5-10x faster for incremental changes
**Complexity:** High - Requires change tracking

**Solution:**
```python
def validate_docs(docs_path, incremental=False, baseline=None):
    if incremental and baseline:
        # Only validate files that changed since baseline
        changed_files = detect_changed_files(docs_path, baseline)
        md_files = [f for f in md_files if f in changed_files]
    else:
        md_files = find_markdown_files(docs_path)

    # ... rest of validation ...
```

**Effort:** 4-6 hours
**Timeline:** Month 3

---

### 15. Baseline Loading Cache
**Tools:** detect_changes, sync, update_baseline
**Performance Impact:** Minor (baselines are small)

**Solution:**
```python
@lru_cache(maxsize=3)
def load_baseline(baseline_path: Path, baseline_type: str):
    with baseline_path.open() as f:
        return json.load(f)
```

**Effort:** 1 hour
**Timeline:** Month 3

---

## LOW Priority (P3) - Backlog

### 16. Extract Platform Markers to Config
**Tool:** docmgr_detect_platform
**Impact:** Minor - Slightly cleaner code

**Effort:** 1 hour
**Timeline:** Backlog

---

### 17. Document Heuristic Thresholds
**Tool:** docmgr_assess_quality
**Impact:** Makes scoring more transparent

**Solution:**
Add `quality-thresholds.yml` configuration.

**Effort:** 1-2 hours
**Timeline:** Backlog

---

### 18. Tune Quality Heuristics
**Tool:** docmgr_assess_quality
**Impact:** More accurate scoring (ongoing)

**Effort:** Ongoing based on user feedback
**Timeline:** Continuous improvement

---

## Implementation Phases

### Phase 1: Critical Fixes (Week 1)
**Effort:** 4-7 hours
**Goals:** Fix data corruption + correctness issues

1. Add file locking to update_baseline (30 min)
2. Make doc paths configurable in detect_changes (4-6 hours)

**Deliverable:** No more data corruption, accurate results for all layouts

---

### Phase 2: High-Impact Performance (Weeks 2-3)
**Effort:** 14-18 hours
**Goals:** 3-5x performance improvement

3. Build link index for validate_docs (2-3 hours)
4. Cache markdown parsing (2-3 hours)
5. Extract shared file scanning (2-3 hours)
6. Extract shared exclude patterns (1-2 hours)
7. Modularize validate_docs (3-4 hours)
8. Modularize assess_quality (3-4 hours)
9. Path index for detect_changes (2-3 hours)

**Deliverable:** Tools run 3-5x faster, complexity reduced from 5→3

---

### Phase 3: Code Quality (Month 2)
**Effort:** 8-10 hours
**Goals:** Improve maintainability

10. Parallelize validators (2 hours)
11. Parallelize analyzers (2 hours)
12. Split `_update_repo_baseline()` (2 hours)
13. Extract categorization patterns (2-3 hours)

**Deliverable:** Code quality 7.3→8.5, 2-3x additional speedup

---

### Phase 4: Advanced Features (Month 3)
**Effort:** 5-7 hours
**Goals:** Incremental validation, polish

14. Incremental validation (4-6 hours)
15. Baseline loading cache (1 hour)

**Deliverable:** 5-10x faster incremental validation

---

### Phase 5: Polish (Backlog)
**Effort:** 3-4 hours
**Goals:** Configuration, tuning

16. Extract platform markers (1 hour)
17. Document heuristic thresholds (1-2 hours)
18. Tune quality heuristics (ongoing)

**Deliverable:** More transparent, configurable quality assessment

---

## Success Metrics

### Performance Metrics
**Baseline (current state, M=50 docs, N=500 files):**
- validate_docs: 12s
- assess_quality: 5s
- detect_changes: 5s
- update_baseline: 6s
- Total workflow: ~33s

**After Phase 1 (Critical):**
- No performance change
- Correctness: 100% accurate for all layouts
- Data safety: No corruption risk

**After Phase 2 (Performance):**
- validate_docs: 4s (67% faster)
- assess_quality: 3s (40% faster)
- detect_changes: 2s (60% faster)
- update_baseline: 4s (33% faster)
- Total workflow: ~16s (51% faster)

**After Phase 3 (Quality + Parallel):**
- validate_docs: 2s (83% faster vs baseline)
- assess_quality: 1.5s (70% faster vs baseline)
- Total workflow: ~8-10s (70-75% faster)

**After Phase 4 (Incremental):**
- Incremental validation: <1s (90% faster for small changes)

### Code Quality Metrics
**Baseline:**
- Average complexity: 3.5/10
- Average code quality: 7.3/10
- Largest file: 771 lines (assess_quality)
- Duplication: ~180 lines across 3 tools

**After Phase 2:**
- Average complexity: 2.8/10 (20% reduction)
- Average code quality: 8.2/10
- Largest file: 150 lines (modularized)
- Duplication: 0 lines (extracted to core)

**After Phase 3:**
- Average complexity: 2.5/10
- Average code quality: 8.7/10

---

## Risk Assessment

### High Risk Items
1. **File locking** - Must test concurrent scenarios thoroughly
2. **Modularization** - Must maintain backward compatibility
3. **Parallel execution** - Must handle race conditions

### Medium Risk Items
4. **Configuration changes** - Need migration guide for existing projects
5. **Cache invalidation** - Must clear caches appropriately

### Low Risk Items
6. **Extract patterns** - Refactoring with tests, low risk
7. **Documentation updates** - No code risk

---

## Testing Strategy

### Phase 1: Critical Fixes
- Test concurrent `update_baseline` calls (5 simultaneous processes)
- Test non-standard doc layouts (10 different structures)
- Test missing config (defaults should work)

### Phase 2: Performance
- Benchmark before/after for each optimization
- Test large projects (M=200 docs, N=2000 files)
- Test cache correctness (stale data detection)

### Phase 3: Quality
- Test each modularized validator independently
- Test parallel execution with various file counts
- Ensure all validators/analyzers still work correctly

### Phase 4: Advanced
- Test incremental validation with git integration
- Test baseline cache invalidation

---

## Related Documentation
- Detailed findings: `README.md`
- Performance analysis: `performance-comparison.md`
- Complexity analysis: `logic-complexity-report.md`
- Architecture diagrams: `temp_mermaid/{tool}_arch/`
