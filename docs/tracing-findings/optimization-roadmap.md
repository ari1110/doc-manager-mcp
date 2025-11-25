# Optimization Roadmap - Prioritized Improvements

## Executive Summary

This document provides a prioritized, actionable roadmap for improving doc-manager based on comprehensive tracing of all 8 tools (100% coverage). Improvements are organized by priority, effort, and impact.

**Quick Stats:**
- **3 CRITICAL** issues (file locking, hardcoded paths, preserve_history)
- **10 HIGH priority** optimizations (performance + complexity + workflows)
- **6 MEDIUM priority** improvements (code quality)
- **3 LOW priority** enhancements (polish)

**Total effort estimate:** 44-59 hours to implement all improvements
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

### 3. Implement preserve_history in migrate
**Tool:** docmgr_migrate
**Issue:** Git history LOST for all migrated files
**Risk Level:** HIGH - Permanent history loss

**Problem:**
```python
# doc_manager_mcp/tools/workflows/migrate.py:276-282
# Parameter exists but NOT IMPLEMENTED
git_mv_count = len([f for f in moved_files if f["method"] == "git mv"])

# But method is ALWAYS "copy" or "preview" (Lines 198, 276)
moved_files.append({
    "old": str(old_file),
    "new": str(new_file),
    "method": "copy"  # ❌ Never uses "git mv"
})
```

Code references `git mv` but only uses `shutil.copy2`, so git history is lost for all migrated files.

**Solution:**
Implement git mv using subprocess:

```python
import subprocess

# In file processing loop (migrate.py:137-200)
if params.preserve_history and is_git_repo(project_path):
    # Use git mv to preserve history
    try:
        subprocess.run(
            ['git', 'mv', str(old_file), str(new_file)],
            cwd=project_path,
            check=True,
            capture_output=True
        )
        method = "git mv"
    except subprocess.CalledProcessError:
        # Fallback to copy if git mv fails
        shutil.copy2(old_file, new_file)
        method = "copy"
else:
    # Standard copy (no git)
    shutil.copy2(old_file, new_file)
    method = "copy"

moved_files.append({..., "method": method})
```

**Effort:** 2-3 hours
**Impact:** Preserves git history for migrations
**Timeline:** This week

**Implementation Steps:**
1. Add helper: `is_git_repo(project_path)` - Check if .git exists
2. Update file processing loop to use subprocess for git mv
3. Add fallback to shutil.copy2 if git mv fails
4. Update method tracking in moved_files
5. Add tests: Verify git history preserved after migration
6. Document in migration tool description

---

## HIGH Priority (P1) - Fix Within 1 Month

### 4. Build Link Index for validate_docs
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

### 5. Cache Markdown Parsing (validate_docs + assess_quality)
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

### 6. Extract Shared File Scanning Logic
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

### 7. Extract Shared Exclude Pattern Building
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

### 8. Modularize validate_docs (Extract 6 Validators)
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

### 9. Modularize assess_quality (Extract 7 Analyzers)
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

### 10. Path Index for detect_changes (Like dependency tracking)
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

### 11. Parallelize validate_docs + assess_quality in sync
**Tool:** docmgr_sync
**Issue:** Sequential execution of independent analysis steps
**Performance Impact:** 2x faster check/resync mode

**Current Flow:**
```python
# doc_manager_mcp/tools/workflows/sync.py:100-150
# Sequential execution - 4-5 steps run one after another
changes = detect_changes(...)       # Step 1
validate = validate_docs(...)       # Step 2 (independent!)
quality = assess_quality(...)       # Step 3 (independent!)
```

Both validate_docs and assess_quality analyze the same markdown files independently. They can run concurrently.

**Solution:**
```python
import asyncio

async def run_sync_check(params):
    # Step 1: Change detection (must run first)
    changes = await detect_changes_async(...)

    # Steps 2-3: Run validation + quality in parallel
    validate_task = validate_docs_async(...)
    quality_task = assess_quality_async(...)

    validate, quality = await asyncio.gather(validate_task, quality_task)

    return build_report(changes, validate, quality)
```

**Combined with markdown cache (item 5):** Massive speedup since both tools share parsed data and run concurrently.

**Effort:** 2 hours
**Impact:** sync 40-50% faster overall
**Timeline:** Week 2

---

### 12. Extract File Processing Helpers (migrate)
**Tool:** docmgr_migrate
**Issue:** 64-line file processing loop with 3-4 nesting levels
**Impact:** Reduces complexity from 4→3

**Current Problem:**
```python
# doc_manager_mcp/tools/workflows/migrate.py:137-200
# 64-line loop with deep nesting - hard to test/maintain
for old_file in existing_docs.rglob("*"):
    if old_file.suffix.lower() in ['.md', '.markdown']:
        content = old_file.read_text()

        # Extract frontmatter (10 lines)
        frontmatter_dict, body = extract_frontmatter(content)

        if params.rewrite_links:  # Nested
            link_mappings = compute_link_mappings(...)
            if link_mappings:  # Double nested
                body = rewrite_links_in_content(body, link_mappings)

        if params.regenerate_toc:  # Nested
            toc = generate_toc(body, max_depth=3)

        if not params.dry_run:  # Nested
            new_file.write_text(final_content)
```

**Solution:**
Extract 3 helper functions:

```python
# workflows/migrate_helpers.py
def process_markdown_file(
    old_file: Path,
    new_file: Path,
    params: MigrateParams,
    link_mappings: dict
) -> dict:
    """Process single markdown file - returns result dict."""
    content = old_file.read_text()
    frontmatter, body = extract_frontmatter(content)

    if params.rewrite_links:
        body = _rewrite_links(body, link_mappings)

    if params.regenerate_toc:
        body = _add_toc(body)

    if not params.dry_run:
        _write_markdown_file(new_file, frontmatter, body, params.preserve_history)

    return {
        "old": str(old_file),
        "new": str(new_file),
        "method": "git mv" if params.preserve_history else "copy"
    }

def _rewrite_links(body: str, mappings: dict) -> str:
    """Rewrite links in markdown body."""
    # Extracted from nested if
    ...

def _add_toc(body: str) -> str:
    """Add table of contents to markdown body."""
    # Extracted from nested if
    ...
```

Main loop becomes:
```python
# Clean 15-line loop
for old_file in existing_docs.rglob("*"):
    if old_file.suffix.lower() in ['.md', '.markdown']:
        result = process_markdown_file(old_file, new_file, params, link_mappings)
        moved_files.append(result)
```

**Effort:** 2-3 hours
**Impact:** Complexity 4→3, much easier to test individual steps
**Timeline:** Week 2-3

---

### 13. Parallelize File Processing (migrate)
**Tool:** docmgr_migrate
**Issue:** Sequential file processing
**Performance Impact:** 3-4x faster for large migrations

**Constraint:** Can only parallelize when preserve_history=False (git mv must be sequential)

**Solution:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def migrate_files_parallel(files, params):
    if params.preserve_history:
        # Must use git mv sequentially
        return migrate_files_sequential(files, params)

    # Parallelize file copying
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = [
            executor.submit(process_markdown_file, f, params)
            for f in files
        ]
        results = [task.result() for task in tasks]

    return results
```

**Effort:** 3-4 hours
**Impact:** migrate 3-4x faster for large projects (when preserve_history=False)
**Timeline:** Week 3

---

## MEDIUM Priority (P2) - Fix Within 3 Months

### 14. Parallelize Validators (validate_docs)
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

### 15. Parallelize Analyzers (assess_quality)
**Tool:** docmgr_assess_quality
**Performance Impact:** 2-3x faster

Similar to #14, run 7 analyzers concurrently.

**Effort:** 2 hours (after modularization)
**Timeline:** Month 2

---

### 16. Split `_update_repo_baseline()` Function
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

### 17. Extract Categorization Patterns (detect_changes)
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

### 18. Incremental Validation (Only Changed Docs)
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

### 19. Baseline Loading Cache
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

### 20. Extract Platform Markers to Config
**Tool:** docmgr_detect_platform
**Impact:** Minor - Slightly cleaner code

**Effort:** 1 hour
**Timeline:** Backlog

---

### 21. Document Heuristic Thresholds
**Tool:** docmgr_assess_quality
**Impact:** Makes scoring more transparent

**Solution:**
Add `quality-thresholds.yml` configuration.

**Effort:** 1-2 hours
**Timeline:** Backlog

---

### 22. Tune Quality Heuristics
**Tool:** docmgr_assess_quality
**Impact:** More accurate scoring (ongoing)

**Effort:** Ongoing based on user feedback
**Timeline:** Continuous improvement

---

## Implementation Phases

### Phase 1: Critical Fixes (Week 1)
**Effort:** 7-10 hours
**Goals:** Fix data corruption + correctness issues

1. Add file locking to update_baseline (30 min)
2. Make doc paths configurable in detect_changes (4-6 hours)
3. Implement preserve_history in migrate (2-3 hours)

**Deliverable:** No more data corruption, accurate results for all layouts, git history preserved in migrations

---

### Phase 2: High-Impact Performance (Weeks 2-3)
**Effort:** 21-28 hours
**Goals:** 3-5x performance improvement

4. Build link index for validate_docs (2-3 hours)
5. Cache markdown parsing (2-3 hours)
6. Extract shared file scanning (2-3 hours)
7. Extract shared exclude patterns (1-2 hours)
8. Modularize validate_docs (3-4 hours)
9. Modularize assess_quality (3-4 hours)
10. Path index for detect_changes (2-3 hours)
11. Parallelize validate_docs + assess_quality in sync (2 hours)
12. Extract file processing helpers in migrate (2-3 hours)
13. Parallelize file processing in migrate (3-4 hours)

**Deliverable:** Tools run 3-5x faster, complexity reduced from 5→3, sync and migrate optimized

---

### Phase 3: Code Quality (Month 2)
**Effort:** 8-10 hours
**Goals:** Improve maintainability

14. Parallelize validators (2 hours)
15. Parallelize analyzers (2 hours)
16. Split `_update_repo_baseline()` (2 hours)
17. Extract categorization patterns (2-3 hours)

**Deliverable:** Code quality 7.3→8.5, 2-3x additional speedup

---

### Phase 4: Advanced Features (Month 3)
**Effort:** 5-7 hours
**Goals:** Incremental validation, polish

18. Incremental validation (4-6 hours)
19. Baseline loading cache (1 hour)

**Deliverable:** 5-10x faster incremental validation

---

### Phase 5: Polish (Backlog)
**Effort:** 3-4 hours
**Goals:** Configuration, tuning

20. Extract platform markers (1 hour)
21. Document heuristic thresholds (1-2 hours)
22. Tune quality heuristics (ongoing)

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
