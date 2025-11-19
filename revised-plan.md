Doc-Manager Enhancement Plan (Revised)

 Context

 Foundation is solid after MarkdownParser refactors:
 - Broken links: 97 → 3 (97% reduction)
 - Duplicate headers: 77 → 20 (74% reduction)
 - Deprecated refs: 59 → 16.3 (73% reduction)
 - TreeSitter working: 4,237 symbols indexed

 Remaining minor issues (code block tags, heading hierarchy) will be addressed separately.

 ---
 Phase 1: Semantic Change Detection (Weeks 1-3)

 Goal

 Add TreeSitter-based semantic diff to changes.py for function signature tracking, new classes, deleted methods.

 Critical Design Decision (from audit)

 Symbol Baseline Lifecycle:
 - Storage: .doc-manager/memory/symbol-baseline.json (separate from repo-baseline.json)
 - Creation: Lazy - only on first map_changes call with semantic mode enabled
 - Loading: Auto-detect if baseline exists, create if missing
 - Update: On each semantic diff run, replace old baseline

 Tasks

 1.1 Create Symbol Baseline Infrastructure
 - New file: indexing/semantic_diff.py
 - SemanticChange dataclass (name, type, old_sig, new_sig, severity, file, line)
 - compare_symbols(old, new) -> list[SemanticChange]
 - load_symbol_baseline(path) -> dict
 - save_symbol_baseline(path, symbols) -> None

 1.2 Add Models
 - Extend models.py with SemanticChange dataclass
 - Add include_semantic: bool = False to MapChangesInput

 1.3 Integrate with changes.py
 - Modify _load_baseline() to optionally load symbols
 - Add _detect_semantic_changes(baseline, current, changed_files)
 - Enhance _format_changes_report() with semantic section
 - Only run semantic diff if include_semantic=True (opt-in)

 1.4 Testing
 - Unit tests: Symbol comparison (Go, Python, TypeScript)
 - Integration test: Detect function signature change in pass-cli
 - Test: Baseline creation, update, loading
 - Test: Lazy loading (no performance impact on normal memory init)

 Files:
 - indexing/semantic_diff.py - NEW (~150 lines)
 - tools/changes.py - MODIFY (add ~100 lines)
 - models.py - MODIFY (add SemanticChange)

 ---
 Phase 2: Smart Link Rewriting (Weeks 4-6)

 Goal

 Add automatic link rewriting to migrate() workflow with frontmatter preservation.

 Critical Note (from audit)

 Link rewriting is net-new functionality - migrate currently only copies files and reports broken links. This is bigger than just  
 "adding parameters."

 Tasks

 2.1 Add python-frontmatter Dependency
 - Update pyproject.toml: python-frontmatter==1.1.0 (pin version)
 - Test with Hugo shortcodes in frontmatter (edge case validation)

 2.2 Create Link Rewriter Module
 - New file: indexing/link_rewriter.py
 - extract_frontmatter(content) -> (dict, str) - uses python-frontmatter
 - compute_link_mappings(file, old_root, new_root) -> dict[str, str]
 - rewrite_links_in_content(content, mappings) -> str - line-based using MarkdownParser
 - generate_toc(content) -> str - from headers
 - update_or_insert_toc(content, toc) -> str

 2.3 Modify Migration Workflow
 - Modify workflows.py::migrate()
 - Replace shutil.copytree() with file-by-file copy loop
 - For each markdown file:
   - Extract frontmatter
   - Compute link mappings
   - Rewrite links
   - Preserve frontmatter
   - Optionally regenerate TOC
 - Add rewrite_links: bool = True to MigrateInput
 - Add regenerate_toc: bool = False to MigrateInput
 - Add --dry-run mode (show changes without applying)

 2.4 Testing
 - Test: Relative link updates (../other.md → ../../other.md)
 - Test: Absolute link updates (/docs/api.md → /new-docs/api.md)
 - Test: Frontmatter with --- in YAML strings (edge case)
 - Test: Hugo shortcodes preservation
 - Test: TOC generation with nested headers
 - Integration: Full migrate workflow with 50+ files

 Files:
 - pyproject.toml - MODIFY (add dependency)
 - indexing/link_rewriter.py - NEW (~250 lines)
 - tools/workflows.py - MODIFY (add ~150 lines to migrate())
 - models.py - MODIFY (extend MigrateInput)

 ---
 Phase 3: Validation & Quality Enhancements (Weeks 7-10)

 Goal

 Add 6 features to validation.py and quality.py while maintaining clear tool boundaries.

 File Size Mitigation (from audit)

 Create helper modules to prevent bloat:
 - tools/validation_helpers.py - code example validation logic
 - tools/quality_helpers.py - style check helpers

 Keep main files as coordinators, extract complex logic to helpers.

 Features to Add

 To validation.py (Correctness)

 3.1 Code Example Semantic Validation (~80 lines)
 - NEW: _validate_code_examples(docs_path, project_path, symbol_index)
 - Verify code examples reference real files in codebase
 - Check file paths mentioned in code blocks exist
 - Report: "Example references missing file: cmd/nonexistent.go"

 3.2 Expose Symbol Validation (~40 lines)
 - CLARIFICATION: Validate that documented symbols exist in code
 - Reuse SymbolIndexer from dependencies.py
 - NEW: _validate_documented_symbols(docs_path, project_path)
 - Extract function/class names from inline code
 - Check against TreeSitter symbol index
 - Report: "Documented symbol OldFunction() not found in codebase"

 To quality.py (Quality/Style)

 3.3 List Formatting Consistency (~60 lines in helpers)
 - NEW: _check_list_consistency(content) -> list[dict]
 - Detect mixed markers (-, *, +) within same document
 - Report predominant style and violations
 - Suggestion: "Standardize on - (used 15/20 times)"

 3.4 Heading Case Consistency (~70 lines in helpers)
 - NEW: _check_heading_case(headers) -> list[dict]
 - Detect: "Title Case" vs "Sentence case"
 - Report predominant style and violations
 - Info-level (not error)

 3.5 Multiple H1 Detection (~30 lines, modify existing)
 - MODIFY: _assess_purposefulness()
 - Currently checks if H1 exists (line 199)
 - Add: Check for MULTIPLE H1s per file
 - Warning: "File has 2 H1 headers - use only one per document"

 3.6 Undocumented API Detection (~100 lines in helpers)
 - NEW: _detect_undocumented_apis(project_path, docs_path, symbol_index)
 - Use SymbolIndexer to find all public symbols
 - Filter: Functions/classes (exclude variables, constants)
 - Cross-reference with inline code in docs
 - Report: "Public function ParseConfig() undocumented"
 - Metric: "18 of 25 public APIs documented (72%)"

 3.7 Coverage Percentage (~50 lines)
 - NEW: _calculate_coverage(documented, total_public) -> dict
 - Metric: (documented / total_public) * 100
 - Report per-file and project-wide
 - Add to quality assessment summary

 Files:
 - tools/validation.py - MODIFY (add ~120 lines)
 - tools/validation_helpers.py - NEW (~100 lines)
 - tools/quality.py - MODIFY (add ~150 lines)
 - tools/quality_helpers.py - NEW (~280 lines)
 - models.py - MODIFY (add flags to inputs)

 ---
 Testing Strategy (from audit feedback)

 Unit Tests

 - Phase 1: Symbol comparison logic (10 tests)
 - Phase 2: Link mapping computation, frontmatter extraction (15 tests)
 - Phase 3: Each quality check independently (30 tests)

 Integration Tests

 - Phase 1: Detect real changes in pass-cli between commits
 - Phase 2: Full migrate workflow with link rewriting
 - Phase 3: Run enhanced tools on pass-cli, verify no false positives

 Performance Tests

 - Symbol indexing: <5s for 1000 files
 - Link rewriting: <10s for 500 markdown files
 - Quality assessment: <30s for 1000 files (no regression)

 ---
 Implementation Order

 Week 1-3: Phase 1 (Semantic Diff)
 - Most valuable for tracking code evolution
 - Builds on proven SymbolIndexer

 Week 4-6: Phase 2 (Link Rewriting)
 - Immediate user value (fixes broken links during migration)
 - Well-scoped, clear deliverable

 Week 7-10: Phase 3 (6 Features)
 - Split into two sprints: 3 features each
 - Week 7-8: List formatting, heading case, multiple H1
 - Week 9-10: Undocumented APIs, coverage %, symbol validation

 ---
 Tool Boundaries (Crystal Clear)

 validation.py = "Find errors to fix"
 - Broken links, missing assets, syntax errors
 - NEW: Code examples reference real files
 - NEW: Documented symbols exist in code

 quality.py = "Find improvements to make"
 - Quality scoring (7 criteria)
 - NEW: Style checks (lists, headings, H1s)
 - NEW: Coverage analysis (undocumented APIs, %)

 No linter.py - all features integrated into existing tools.

 ---
 Risk Mitigation

 Lazy Loading: Symbol baseline only created when needed (no memory init impact)
 Helper Modules: Prevent file bloat (keep main files <700 lines)
 Dry-Run Mode: Link rewriting shows changes before applying
 Opt-In Semantic: Semantic diff only runs if explicitly requested
 Testing First: Each feature has unit tests before integration

 ---
 Success Criteria

 Phase 1: map_changes --semantic reports "func SaveVault() signature changed in vault.go:42"
 Phase 2: Migration automatically fixes broken internal links, preserves frontmatter
 Phase 3: Quality assessment reports list formatting issues, API coverage %, all new checks tested

 ---
 Total Scope

 - 3 phases, 13 features, 4 new files, 7 modified files
 - 1 new dependency (python-frontmatter)
 - ~1,200 lines of new code (including helpers)
 - ~55 new tests
 - 10 weeks (realistic timeline incorporating audit feedback)
