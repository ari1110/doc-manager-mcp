# Logic Complexity Report - All Traced Tools

## Executive Summary

This document provides detailed logic complexity analysis for all 8 traced doc-manager tools, including complexity ratings, code structure metrics, maintainability assessment, and refactoring recommendations.

**Key Findings:**
- 2 tools rated "Very Complex" (5/10): validate_docs, assess_quality
- 2 tools rated "Complex" (4/10): detect_changes, migrate
- Average complexity: 3.4/10 - Moderate overall
- Main complexity drivers: Large files (500+ lines), hardcoded values, multiple responsibilities
- Workflow orchestrators generally have moderate complexity (3-4/10)

**Complexity Rating Scale:**
- **1 (Trivial)** - Single responsibility, <50 lines, no nesting
- **2 (Simple)** - Clear flow, <200 lines, minimal nesting
- **3 (Moderate)** - Some complexity, <300 lines, 2-3 levels of nesting
- **4 (Complex)** - Multiple concerns, >400 lines, hardcoded logic
- **5 (Very Complex)** - Many responsibilities, >500 lines, needs refactoring

---

## Complexity Summary Table

| Tool | Rating | LOC | Functions | Nesting | Cyclomatic | Main Issues |
|------|--------|-----|-----------|---------|------------|-------------|
| **docmgr_init** | 2 (Simple) | 154 | 4 | 2 levels | ~8 | None - Clean orchestrator |
| **docmgr_update_baseline** | 3 (Moderate) | 284 | 6 | 3 levels | ~15 | Long function (109 lines) |
| **docmgr_detect_platform** | 2 (Simple) | 291 | 8 | 2 levels | ~12 | Repeated code patterns |
| **docmgr_detect_changes** | 4 (Complex) | 732 | 15+ | 3-4 levels | ~30 | Hardcoded paths + patterns |
| **docmgr_validate_docs** | 5 (Very Complex) | 573 | 13 | 3-4 levels | ~45 | 6 validators in one file |
| **docmgr_assess_quality** | 5 (Very Complex) | 771 | 10+ | 3-4 levels | ~40 | 7 analyzers + fuzzy logic |
| **docmgr_sync** | 3 (Moderate) | 286 | 1 | 2-3 levels | ~10 | step_offset handling, report building |
| **docmgr_migrate** | 4 (Complex) | 329 | 1 | 3-4 levels | ~20 | File processing loop (64 lines, 3-4 nesting) |

**Average Complexity: 3.4/10** (Moderate)

---

## Detailed Analysis by Tool

### 1. docmgr_init
**Location:** `doc_manager_mcp/tools/state/init.py:22`
**Complexity Rating: 2/10 (Simple)**

#### Metrics
- **Lines of Code:** 154
- **Functions:** 4 (1 main + 3 helpers)
- **Max Nesting:** 2 levels
- **Cyclomatic Complexity:** ~8
- **Longest Function:** `docmgr_init()` - 45 lines

#### Structure
```
docmgr_init()                    [45 lines] - Main orchestrator
├── _create_config()             [30 lines] - Config file creation
├── _create_repo_baseline()      [25 lines] - File scanning
├── _create_memory_baseline()    [20 lines] - Symbol extraction
└── _create_dependencies()       [25 lines] - Mapping creation
```

#### Code Quality: 9/10
**Strengths:**
✅ Clear separation of concerns
✅ Single responsibility per function
✅ Minimal nesting (max 2 levels)
✅ Good error handling
✅ Well-named functions

**Minor Issues:**
⚠️ Silent config overwrite (doesn't warn if .doc-manager.yml exists)

#### Example - Clean Orchestration Pattern
```python
# doc_manager_mcp/tools/state/init.py:22-66
def docmgr_init(...):
    """Clean orchestrator pattern - low complexity"""
    config_path = project_path / ".doc-manager.yml"

    # Step 1: Create config
    _create_config(config_path, sources, docs_path, platform, ...)

    # Step 2: Create baselines (3 independent operations)
    _create_repo_baseline(project_path, ...)
    _create_memory_baseline(project_path, ...)
    _create_dependencies(project_path, ...)

    return {"status": "success", ...}
```

**Why it's simple:**
- Linear flow, no complex branching
- Each helper does one thing
- No hardcoded values
- Easy to test and maintain

#### Recommendations: None needed - Already well-structured

---

### 2. docmgr_update_baseline
**Location:** `doc_manager_mcp/tools/state/update_baseline.py:10`
**Complexity Rating: 3/10 (Moderate)**

#### Metrics
- **Lines of Code:** 284
- **Functions:** 6 (1 main + 5 helpers)
- **Max Nesting:** 3 levels
- **Cyclomatic Complexity:** ~15
- **Longest Function:** `_update_repo_baseline()` - **109 lines** ⚠️

#### Structure
```
update_baseline()                       [35 lines] - Orchestrator
├── _update_repo_baseline()             [109 lines] ⚠️ - File scanning + checksums
├── _update_symbol_baseline()           [55 lines] - TreeSitter parsing
├── _update_dependencies()              [45 lines] - Dependency mapping
└── Shared logic from dependency module [~40 lines reused]
```

#### Code Quality: 7/10
**Strengths:**
✅ Reuses dependency tracking logic
✅ Atomic baseline updates
✅ Good error handling

**Issues:**
🔴 `_update_repo_baseline()` too long (109 lines) - Should split into smaller functions
🔴 **Missing file locking** - Race conditions possible (CRITICAL)
⚠️ Duplicate file scanning logic (also in init, detect_changes)

#### Example - Long Function Problem
```python
# doc_manager_mcp/tools/state/update_baseline.py:93-201
def _update_repo_baseline(project_path, sources, ...):
    """109 lines - TOO LONG"""

    # 1. Build exclude patterns (15 lines)
    exclude_patterns = []
    if use_gitignore:
        # ... gitignore logic ...
    exclude_patterns.extend(custom_patterns)

    # 2. Scan project files (30 lines)
    baseline = {"files": {}, "metadata": {...}}
    for root, dirs, files in os.walk(project_path):
        # ... complex filtering ...
        for file in files:
            # ... categorization logic ...
            baseline["files"][rel_path] = {...}

    # 3. Calculate checksums (20 lines)
    for file_path in baseline["files"]:
        # ... checksum calculation ...

    # 4. Write baseline (10 lines)
    # ... JSON serialization ...

    # 5. Return (5 lines)
    return baseline
```

**Why it's moderate complexity:**
- 5 distinct responsibilities in one function
- 3 levels of nesting (walk → filter → process)
- Could be 5 separate functions

#### Recommendations
**Priority: MEDIUM**
1. **Split `_update_repo_baseline()`** into 5 functions:
   ```python
   def _update_repo_baseline(...):
       exclude = _build_exclude_patterns(...)
       files = _scan_project_files(project_path, exclude)
       baseline = _categorize_files(files)
       _calculate_checksums(baseline)
       _write_baseline(baseline_path, baseline)
   ```
2. **Add file locking** (CRITICAL - see correctness issues)
3. **Extract shared scanning logic** to core/patterns.py

---

### 3. docmgr_detect_platform
**Location:** `doc_manager_mcp/tools/analysis/platform.py`
**Complexity Rating: 2/10 (Simple)**

#### Metrics
- **Lines of Code:** 291
- **Functions:** 8 (1 main + 7 helpers)
- **Max Nesting:** 2 levels
- **Cyclomatic Complexity:** ~12
- **Longest Function:** `docmgr_detect_platform()` - 40 lines

#### Structure
```
docmgr_detect_platform()                [40 lines] - 3-stage detection
├── _check_root_configs()               [35 lines] - Platform config files
├── _check_doc_directories()            [45 lines] - Doc-specific configs
├── _check_dependencies()               [30 lines] - package.json, requirements.txt
└── _recommend_platform()               [50 lines] - Recommendation logic
```

#### Code Quality: 8/10
**Strengths:**
✅ Clean 3-stage detection flow
✅ Well-separated concerns
✅ Minimal nesting
✅ O(1) complexity - Already optimal

**Minor Issues:**
⚠️ Repeated code in `_check_doc_directories()` - Similar checks for different platforms

#### Example - Repeated Pattern
```python
# doc_manager_mcp/tools/analysis/platform.py:~120-180
def _check_doc_directories(project_path: Path):
    """Repeated pattern for each platform"""

    # MkDocs check
    docs_dir = project_path / "docs"
    if docs_dir.exists():
        if (docs_dir / "mkdocs.yml").exists():
            return "mkdocs"

    # Sphinx check
    if docs_dir.exists():
        if (docs_dir / "conf.py").exists():
            return "sphinx"

    # Hugo check (similar pattern)
    if docs_dir.exists():
        if (docs_dir / "config.toml").exists():
            return "hugo"

    # ... 4 more similar checks
```

**Could be refactored to:**
```python
PLATFORM_MARKERS = {
    "mkdocs": ["mkdocs.yml", "mkdocs.yaml"],
    "sphinx": ["conf.py", "_build/"],
    "hugo": ["config.toml", "config.yaml"],
    # ...
}

def _check_doc_directories(project_path: Path):
    docs_dir = project_path / "docs"
    if not docs_dir.exists():
        return None

    for platform, markers in PLATFORM_MARKERS.items():
        if any((docs_dir / marker).exists() for marker in markers):
            return platform
```

#### Recommendations
**Priority: LOW**
1. **Extract platform markers** to configuration dict (1 hour)
2. **Reduce repeated checking** with data-driven approach (1 hour)

---

### 4. docmgr_detect_changes
**Location:** `doc_manager_mcp/tools/analysis/detect_changes.py` + `tools/_internal/changes.py`
**Complexity Rating: 4/10 (Complex)**

#### Metrics
- **Lines of Code:** 732 (203 main + 529 shared)
- **Functions:** 15+ (3 main + 12+ helpers)
- **Max Nesting:** 3-4 levels
- **Cyclomatic Complexity:** ~30
- **Longest Function:** `_map_to_affected_docs()` - 80 lines with **9 hardcoded paths** 🔴

#### Structure
```
docmgr_detect_changes()                 [85 lines] - Mode selection
├── _detect_changes_checksum()          [45 lines] - Checksum comparison
├── _detect_changes_git_diff()          [60 lines] - Git parsing
└── Shared logic (changes.py)           [529 lines]
    ├── _categorize_changed_file()      [120 lines] - 15+ hardcoded patterns
    ├── _map_to_affected_docs()         [80 lines] - **9 hardcoded doc paths** 🔴
    ├── _extract_semantic_changes()     [160 lines] - TreeSitter parsing
    └── Helper functions                [~170 lines]
```

#### Code Quality: 6/10
**Strengths:**
✅ Supports 2 modes (checksum + git diff)
✅ Semantic analysis with TreeSitter
✅ Categorization logic

**Critical Issues:**
🔴 **Hardcoded file patterns** - 15+ patterns in `_categorize_changed_file()`
🔴 **Hardcoded doc paths** - 9 paths in `_map_to_affected_docs()` (CRITICAL)
⚠️ Large shared module (529 lines) - Should be split

#### Example - Hardcoded Paths Problem
```python
# doc_manager_mcp/tools/_internal/changes.py:260-339
def _map_to_affected_docs(changed_files, category, project_path):
    """80 lines with 9 HARDCODED doc paths"""
    affected_docs = []

    if category == "cli":
        _add_affected_doc(
            affected_docs,
            "docs/reference/command-reference.md",  # HARDCODED ❌
            f"CLI implementation changed: {file_path}",
            "high",
            file_path
        )

    elif category == "core":
        _add_affected_doc(
            affected_docs,
            "docs/architecture/core-architecture.md",  # HARDCODED ❌
            ...
        )

    # ... 7 more hardcoded paths for different categories ...

    elif category == "dependencies":
        _add_affected_doc(
            affected_docs,
            "docs/reference/dependency-tracking.md",  # HARDCODED ❌
            ...
        )
```

**Why this is a CRITICAL issue:**
- Fails for projects with non-standard doc layouts
- No way to configure paths per project
- Duplicate "docs/" prefix assumption
- Breaks if docs are in `documentation/`, `wiki/`, etc.

**Impact on complexity:**
- Adds 80 lines of repetitive code
- Makes function hard to test (needs specific file structure)
- Requires code changes for different projects

#### Recommendations
**Priority: CRITICAL**
1. **Make doc paths configurable** in .doc-manager.yml (4-6 hours):
   ```yaml
   # .doc-manager.yml
   doc_paths:
     cli: "docs/reference/command-reference.md"
     core: "docs/architecture/core-architecture.md"
     dependencies: "docs/reference/dependency-tracking.md"
     # ... configurable per project
   ```
2. **Extract categorization patterns** to patterns.py (2-3 hours)
3. **Split changes.py** into smaller modules (3-4 hours)

---

### 5. docmgr_validate_docs
**Location:** `doc_manager_mcp/tools/analysis/validation/validator.py`
**Complexity Rating: 5/10 (Very Complex)**

#### Metrics
- **Lines of Code:** 573 (LARGEST single-file tool)
- **Functions:** 13 (1 main + 6 validators + 6 helpers)
- **Max Nesting:** 3-4 levels
- **Cyclomatic Complexity:** ~45
- **Validation Types:** 6 (conventions, links, assets, snippets, syntax, symbols)
- **Issue Types Detected:** 20+

#### Structure
```
validate_docs()                         [90 lines] - Main orchestrator
├── _validate_conventions()             [48 lines] - Convention checking
├── _check_broken_links()               [41 lines] - Link resolution
│   ├── _extract_links()                [25 lines] - Markdown + HTML parsing
│   └── _is_hugo_shortcode()            [10 lines] - Hugo detection
├── _validate_assets()                  [71 lines] - Image checking
│   └── _extract_images()               [30 lines] - Image extraction
├── _validate_code_snippets()           [52 lines] - Basic syntax
│   └── TreeSitter integration
├── _validate_code_syntax()             [29 lines] - Deep validation
│   └── CodeValidator integration
└── _validate_symbols()                 [40 lines] - Symbol verification
    └── SymbolIndexer integration
```

#### Code Quality: 7/10
**Strengths:**
✅ Comprehensive - 6 validation types
✅ MarkdownParser integration
✅ TreeSitter for accurate syntax checking
✅ Hugo support (shortcodes, extensionless links)
✅ Symlink safety (recursion protection)

**Issues:**
🔴 **573 lines in single file** - Should extract validators to separate modules
🔴 **Nested loops** - 3-4 levels deep in validation logic
⚠️ **Repeated markdown parsing** - Each validator re-parses files
⚠️ **No parallelization** - 6 validators run sequentially

#### Example - Nested Loop Complexity
```python
# doc_manager_mcp/tools/analysis/validation/validator.py:483-572
def validate_docs(docs_path, check_links=True, check_assets=True, ...):
    """90 lines - Orchestrates 6 validators"""
    issues = []

    # Find all markdown files
    md_files = find_markdown_files(docs_path)  # M files

    # Validator 1: Conventions
    if check_links:
        for file in md_files:                    # Loop 1: M iterations
            content = file.read_text()
            links = extract_links(content)
            for link in links:                    # Loop 2: L iterations
                # Check link validity
                for target in possible_targets:   # Loop 3: M iterations (WORST CASE)
                    if resolve_link(link, target):
                        break
                else:
                    issues.append(...)            # O(M×L×M) - QUADRATIC!

    # Validator 2: Assets (similar nesting)
    if check_assets:
        for file in md_files:                    # Loop 1
            images = extract_images(file)
            for image in images:                  # Loop 2
                # Check image exists

    # ... 4 more validators with similar nesting ...

    return issues
```

**Nesting levels:**
- Level 1: Markdown files loop (M)
- Level 2: Elements loop (links/images/blocks per file)
- Level 3: Validation checks per element
- Level 4: Sometimes nested conditionals within checks

#### Recommendations
**Priority: HIGH**
1. **Extract validators to separate modules** (3-4 hours):
   ```
   validation/
   ├── validator.py          [100 lines] - Main orchestrator
   ├── conventions.py        [80 lines] - Convention validator
   ├── links.py              [100 lines] - Link validator
   ├── assets.py             [100 lines] - Asset validator
   ├── snippets.py           [80 lines] - Snippet validator
   ├── syntax.py             [60 lines] - Syntax validator
   └── symbols.py            [80 lines] - Symbol validator
   ```

2. **Build link index** to eliminate quadratic complexity (2-3 hours)
3. **Cache markdown parsing** (2-3 hours)
4. **Parallelize validators** with asyncio (2 hours)

---

### 6. docmgr_assess_quality
**Location:** `doc_manager_mcp/tools/analysis/quality/assessment.py`
**Complexity Rating: 5/10 (Very Complex)**

#### Metrics
- **Lines of Code:** 771 (2nd LARGEST tool)
- **Functions:** 10+ (1 main + 7 analyzers + helpers)
- **Max Nesting:** 3-4 levels
- **Cyclomatic Complexity:** ~40
- **Quality Criteria:** 7 (relevance, accuracy, purposefulness, uniqueness, consistency, clarity, structure)
- **Heuristics:** 15+ scoring rules

#### Structure
```
assess_quality()                        [120 lines] - Main orchestrator
├── analyze_relevance()                 [70 lines] - Check dates, deprecated refs
├── analyze_accuracy()                  [85 lines] - Compare with codebase
├── analyze_purposefulness()            [60 lines] - Check goals, audience
├── analyze_uniqueness()                [90 lines] - Detect duplication
├── analyze_consistency()               [95 lines] - Terminology, style
├── analyze_clarity()                   [80 lines] - Complexity metrics
└── analyze_structure()                 [75 lines] - Hierarchy, TOC
```

#### Code Quality: 7/10
**Strengths:**
✅ Comprehensive - 7 quality dimensions
✅ Quantitative scoring (good/fair/poor)
✅ MarkdownParser integration
✅ Clear criteria definitions

**Issues:**
🔴 **771 lines in single file** - 2nd largest tool, needs modularization
⚠️ **Fuzzy heuristics** - Not deterministic, scoring can be inconsistent
⚠️ **Repeated parsing** - MarkdownParser called multiple times per file
⚠️ **No caching** - Re-processes same files across criteria

#### Example - Fuzzy Heuristic Logic
```python
# doc_manager_mcp/tools/analysis/quality/assessment.py:~300-350
def analyze_relevance(docs_path):
    """70 lines - Heuristic scoring"""
    findings = []

    for md_file in find_markdown_files(docs_path):
        content = md_file.read_text()

        # Heuristic 1: Check last updated (fuzzy)
        if "Last updated:" in content:
            date_str = extract_date(content)
            age_days = (datetime.now() - parse_date(date_str)).days

            if age_days > 365:                     # THRESHOLD: Arbitrary? ⚠️
                findings.append("Possibly outdated (>1 year)")
            elif age_days > 180:                   # THRESHOLD: Why 180? ⚠️
                findings.append("May need review (>6 months)")

        # Heuristic 2: Check for deprecated terms (fuzzy matching)
        deprecated_terms = ["deprecated", "obsolete", "legacy", "old"]
        for term in deprecated_terms:
            if term in content.lower():            # Simple string match ⚠️
                findings.append(f"Contains '{term}' - verify relevance")

        # Heuristic 3: Cross-reference with codebase (expensive)
        apis_mentioned = extract_api_refs(content)
        for api in apis_mentioned:
            if not exists_in_codebase(api):        # Potentially slow ⚠️
                findings.append(f"API {api} not found in codebase")

    # Score based on findings count (fuzzy thresholds)
    if len(findings) == 0:
        return {"score": "good", ...}
    elif len(findings) < 5:                        # THRESHOLD: Arbitrary? ⚠️
        return {"score": "fair", ...}
    else:
        return {"score": "poor", ...}
```

**Why fuzzy logic increases complexity:**
- Arbitrary thresholds (365 days, 180 days, 5 findings)
- Simple string matching (misses context)
- Potentially expensive cross-referencing
- Non-deterministic results (thresholds may need tuning)

#### Recommendations
**Priority: MEDIUM**
1. **Extract analyzers to separate modules** (3-4 hours):
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

2. **Cache markdown parsing** (2-3 hours)
3. **Document heuristic thresholds** in configuration (1-2 hours):
   ```yaml
   # .doc-manager.yml or separate quality-config.yml
   quality_thresholds:
     relevance:
       max_age_days_warning: 180
       max_age_days_critical: 365
     consistency:
       min_term_similarity: 0.8
     # ... configurable thresholds
   ```

4. **Tune heuristics** based on feedback (ongoing)

---

### 7. docmgr_sync
**Location:** `doc_manager_mcp/tools/workflows/sync.py`
**Complexity Rating: 3/10 (Moderate)**

#### Metrics
- **Lines:** 286
- **Functions:** 1 main (async)
- **Orchestrated tools:** 4
- **Modes:** 2 (check, resync)
- **Conditional branches:** ~10 (mode checks, existence checks, result checks)
- **Nesting:** 2-3 levels (if/else + tool calls)

#### Structure
```
sync()                          [286 lines] - Main orchestrator
├── Validation & setup          [~30 lines]
├── Step 1 (resync): update_baseline  (optional)
├── Step 1/2: detect_changes    [orchestrated]
├── Step 2/3: affected_docs     [simple mapping]
├── Step 3/4: validate_docs     [orchestrated]
├── Step 4/5: assess_quality    [orchestrated]
├── Step 5/6: recommendations   [report building]
└── Summary                     [~30 lines]
```

#### Code Quality: 8/10
**Strengths:**
✅ Single Responsibility: Orchestrates other tools, doesn't duplicate their logic
✅ Clear mode separation with early branching
✅ Comprehensive error handling
✅ Good use of async/await for sub-tool calls
✅ Descriptive docstring with examples

**Minor Issues:**
⚠️ `step_offset` variable feels like a workaround (could use separate functions for each mode)
⚠️ Report line accumulation could be encapsulated in a ReportBuilder class
⚠️ Some repetition in report formatting

#### Example - step_offset Handling
```python
# doc_manager_mcp/tools/workflows/sync.py:100-127
step_offset = 0
if params.mode == "resync":
    lines.append("## Step 1: Updating Baselines")
    # ... update baselines ...
    step_offset = 1  # All subsequent step numbers offset by 1

# Step numbering becomes mode-dependent
lines.append(f"## Step {1 + step_offset}: Change Detection")
lines.append(f"## Step {2 + step_offset}: Affected Documentation")
lines.append(f"## Step {3 + step_offset}: Current Documentation Status")
# ...
```

**Why this adds complexity:**
- Mode-dependent step numbering throughout
- Have to remember offset when adding new steps
- Could be cleaner with separate functions

#### Recommendations
**Priority: LOW (already moderate complexity)**
1. **Refactor mode handling** (2-3 hours):
   ```python
   def _run_check_mode(...):
       # 4-step workflow, no offset needed
       ...

   def _run_resync_mode(...):
       # 5-step workflow with baseline update
       ...

   def sync(...):
       if params.mode == "check":
           return _run_check_mode(...)
       else:
           return _run_resync_mode(...)
   ```

2. **Extract report builder** (1-2 hours):
   ```python
   class SyncReportBuilder:
       def add_header(...)
       def add_conventions(...)
       def add_step_changes(...)
       def build() -> str
   ```

---

### 8. docmgr_migrate
**Location:** `doc_manager_mcp/tools/workflows/migrate.py`
**Complexity Rating: 4/10 (Complex)**

#### Metrics
- **Lines:** 329
- **Functions:** 1 main (async) + 6 imported link transform helpers
- **Orchestrated tools:** 3 (assess_quality, detect_platform, validate_docs)
- **Modes:** 2 (dry run, actual migration)
- **Nesting:** 3-4 levels (if/for/if/for in file processing loop)
- **Cyclomatic Complexity:** ~20
- **File processing:** Loop with markdown special handling

#### Structure
```
migrate()                                   [329 lines] - Main orchestrator
├── Validation & setup                      [~40 lines]
├── Step 1: assess_quality (pre)            [orchestrated]
├── Step 2: detect_platform                 [orchestrated]
├── Step 3: File processing loop            [64 lines] ⚠️ COMPLEX
│   ├── For each file in source             [loop]
│   │   ├── If markdown:                    [nested if]
│   │   │   ├── Extract frontmatter
│   │   │   ├── If rewrite_links:           [nested if]
│   │   │   │   └── Compute + apply mappings
│   │   │   ├── If regenerate_toc:          [nested if]
│   │   │   │   └── Generate + insert TOC
│   │   │   └── Write file (if not dry run)
│   │   └── Else (non-markdown):
│   │       └── Copy file (if not dry run)
│   └── Track moved file
├── Step 4: validate_docs (post)            [orchestrated, if not dry run]
├── Step 5: assess_quality (post)           [orchestrated, if not dry run]
└── Summary + next steps                    [~60 lines]
```

#### Code Quality: 7/10
**Strengths:**
✅ Comprehensive 5-step migration workflow
✅ Dry run mode for safe preview
✅ Reuses link transform utilities
✅ Good error handling

**Issues:**
🔴 **File processing loop complexity** (Lines 137-200)
- 64 lines with 3-4 levels of nesting
- Multiple conditional branches (dry_run, markdown, rewrite_links, regenerate_toc)
- Could be extracted to helper functions

⚠️ **No git mv implementation** - preserve_history parameter exists but not implemented
⚠️ **Link rewriting assumes relative paths** - May not handle all edge cases
⚠️ **No rollback on failure** - Partial migrations leave inconsistent state

#### Example - File Processing Loop Complexity
```python
# doc_manager_mcp/tools/workflows/migrate.py:137-200
for old_file in existing_docs.rglob("*"):  # Loop 1
    if not old_file.is_file():
        continue

    relative_path = old_file.relative_to(existing_docs)
    new_file = new_docs / relative_path

    if old_file.suffix.lower() in ['.md', '.markdown']:  # If 1
        content = old_file.read_text(encoding='utf-8')
        frontmatter_dict, body = extract_frontmatter(content)

        if params.rewrite_links:  # If 2 (nested)
            link_mappings = compute_link_mappings(...)
            if link_mappings:  # If 3 (nested)
                body = rewrite_links_in_content(body, link_mappings)
                links_rewritten += 1

        if params.regenerate_toc and '<!-- TOC -->' in content:  # If 2 (nested)
            toc = generate_toc(body, max_depth=3)
            body = update_or_insert_toc(body, toc)
            tocs_generated += 1

        final_content = preserve_frontmatter(frontmatter_dict, body) if frontmatter_dict else body

        if not params.dry_run:  # If 3 (nested)
            new_file.write_text(final_content, encoding='utf-8')
    else:  # Else 1
        if not params.dry_run:  # If 2 (nested)
            shutil.copy2(old_file, new_file)

    moved_files.append({...})
```

**Why this is complex:**
- 64 lines in one loop
- 3-4 levels of nesting
- 5 distinct responsibilities: read, extract, rewrite, generate TOC, write
- Multiple mode checks (dry_run, rewrite_links, regenerate_toc)

#### Recommendations
**Priority: HIGH**
1. **Extract file processing helpers** (2-3 hours):
   ```python
   def _process_markdown_file(old_file, new_file, params, stats):
       # Lines 148-189
       ...

   def _process_non_markdown_file(old_file, new_file, params):
       # Lines 190-194
       ...

   def _process_file(old_file, existing_docs, new_docs, params, stats):
       # Lines 137-200 becomes:
       relative_path = old_file.relative_to(existing_docs)
       new_file = new_docs / relative_path

       if old_file.suffix.lower() in ['.md', '.markdown']:
           return _process_markdown_file(old_file, new_file, params, stats)
       else:
           return _process_non_markdown_file(old_file, new_file, params)
   ```

2. **Implement preserve_history** (2-3 hours) - See CRITICAL issues
3. **Implement rollback/transaction** (3-4 hours)
4. **Improve link rewriting** (2-3 hours) - Handle edge cases

---

## Cross-Tool Complexity Patterns

### Pattern 1: Simple Orchestrators (Complexity 2)
**Tools:** init, detect_platform

**Characteristics:**
- Linear flow, minimal branching
- Delegate to focused helper functions
- Each helper does one thing
- Easy to test and maintain

**Why they work well:**
```
Main function (30-50 lines):
  1. Validate inputs
  2. Call helper A (focused task)
  3. Call helper B (focused task)
  4. Call helper C (focused task)
  5. Aggregate results
  6. Return
```

**Lesson:** Keep orchestrators thin, push complexity to helpers

---

### Pattern 2: Moderate Complexity (Complexity 3)
**Tool:** update_baseline

**Characteristics:**
- Some long functions (100+ lines)
- 3 levels of nesting
- Mix of responsibilities in one function

**Why complexity increases:**
- Long functions with multiple steps
- Mixing I/O, logic, and data transformation
- Not splitting into smaller units

**Lesson:** Functions >50 lines should be split

---

### Pattern 3: High Complexity (Complexity 4)
**Tool:** detect_changes

**Characteristics:**
- Hardcoded values (patterns, paths)
- Large shared modules (500+ lines)
- Configuration embedded in code

**Why complexity increases:**
- Hardcoded values make code rigid
- No separation of config from logic
- Large modules mix concerns

**Lesson:** Extract configuration, split large modules

---

### Pattern 4: Very High Complexity (Complexity 5)
**Tools:** validate_docs, assess_quality

**Characteristics:**
- 500+ lines in single file
- Multiple responsibilities (6-7 validators/analyzers)
- Nested loops (3-4 levels)
- Fuzzy/heuristic logic

**Why complexity explodes:**
- Violation of Single Responsibility Principle
- All validators/analyzers in one file
- Repeated work (parsing, scanning)

**Lesson:** One validator/analyzer per file, max 100 lines each

---

## Refactoring Recommendations Summary

### HIGH Priority - Reduce Critical Complexity
1. **Make doc paths configurable** in detect_changes (4-6 hours)
   - Move 9 hardcoded paths to .doc-manager.yml
   - Impact: Fixes correctness + reduces complexity

2. **Modularize validate_docs** (3-4 hours)
   - Extract 6 validators to separate files
   - Impact: 573 lines → 6 files of ~80-100 lines each

3. **Modularize assess_quality** (3-4 hours)
   - Extract 7 analyzers to separate files
   - Impact: 771 lines → 7 files of ~90-120 lines each

**Total effort:** 10-14 hours
**Total impact:** Reduces complexity from 5→3 for largest tools

---

### MEDIUM Priority - Improve Maintainability
4. **Split `_update_repo_baseline()`** in update_baseline (2 hours)
   - 109 lines → 5 functions of ~20 lines each

5. **Extract file scanning** to core/patterns.py (2-3 hours)
   - Removes duplication in 3 tools

6. **Extract exclude patterns** to core/patterns.py (1-2 hours)
   - Removes duplication in 3 tools

**Total effort:** 5-7 hours

---

### LOW Priority - Polish
7. **Extract platform markers** in detect_platform (1 hour)
   - Data-driven approach vs. repeated code

8. **Document heuristic thresholds** in assess_quality (1-2 hours)
   - Configuration for scoring rules

**Total effort:** 2-3 hours

---

## Code Quality Summary

| Tool | Current Quality | After Refactoring | Effort |
|------|-----------------|-------------------|--------|
| **docmgr_init** | 9/10 ✅ | No change needed | 0 hours |
| **docmgr_update_baseline** | 7/10 | 8/10 | 2 hours |
| **docmgr_detect_platform** | 8/10 | 9/10 | 1 hour |
| **docmgr_detect_changes** | 6/10 ⚠️ | 8/10 | 6-9 hours |
| **docmgr_validate_docs** | 7/10 ⚠️ | 9/10 | 5-7 hours |
| **docmgr_assess_quality** | 7/10 ⚠️ | 8/10 | 5-6 hours |

**Current average: 7.3/10**
**After refactoring: 8.7/10**

**Total effort: 19-25 hours** for complete refactoring

---

## Related Documentation
- Individual tool complexity sections in `temp_mermaid/{tool}_arch/README.md`
- Performance analysis: `performance-comparison.md`
- Implementation plan: `optimization-roadmap.md`
