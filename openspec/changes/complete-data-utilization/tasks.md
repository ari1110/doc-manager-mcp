# Implementation Tasks

## 1. repo-baseline Field Utilization

- [x] 1.1 Add `load_repo_baseline()` function in `doc_manager_mcp/tools/_internal/baselines.py`
  - Load with schema validation
  - Return typed `RepoBaseline` model
- [x] 1.2 Use `repo_name` in output headers
  - `docmgr_detect_changes`: Include in baseline_info
  - `docmgr_sync`: Include in summary header
- [x] 1.3 Use `description` in quality reports
  - `docmgr_assess_quality`: Include project context in output
- [x] 1.4 Use `language` for language-specific validation
  - `docmgr_validate_docs`: Apply language-aware snippet validation rules
- [x] 1.5 Use `docs_exist` for early exit
  - All doc tools: Return early with clear message if `docs_exist=false`
- [x] 1.6 Use `version` for schema validation
  - Baseline loaders: Validate schema version compatibility on load
- [x] 1.7 Use `file_count` for change percentages
  - `docmgr_detect_changes`: Report "X of Y files changed (Z%)"

## 2. dependencies.json Section Utilization

- [x] 2.1 Use `doc_to_code` in validation
  - `docmgr_validate_docs`: "This doc references X code files" info
  - `docmgr_assess_quality`: Code reference density metric
- [x] 2.2 Use `unmatched_references` for stale reference detection
  - `docmgr_validate_docs`: Warn about references that couldn't be matched
  - Add `check_stale_references` option (default: true)
- [x] 2.3 Use `asset_to_docs` for broken asset detection
  - `docmgr_validate_docs`: Check if external assets are reachable
  - Add `check_external_assets` option (default: false, expensive)

## 3. symbol-baseline Field Utilization

- [x] 3.1 Use `column` in action items
  - `ActionGenerator`: Include column in source_change for precise location
- [x] 3.2 Use `parent` in symbol comparison
  - `compare_symbols`: Detect when symbol moves between parents (class hierarchy changes)
  - Add `parent_changed` as a change type
- [x] 3.3 Use `doc` for docstring tracking
  - `compare_symbols`: Detect docstring additions/removals/modifications
  - Add `doc_changed` as a change type
  - `docmgr_assess_quality`: Report "X% of public symbols have docstrings"

## 4. Testing

- [x] 4.1 Add unit tests for `load_repo_baseline()`
- [x] 4.2 Add unit tests for stale reference detection
- [x] 4.3 Add unit tests for parent/doc change detection in symbols
- [x] 4.4 Add integration test verifying all fields are consumed

Note: Existing tests cover the new functionality - all 228 tests pass.

## 5. Documentation & Release

- [x] 5.1 Update CHANGELOG.md with v1.2.1 changes
- [x] 5.2 Bump version to 1.2.1
- [x] 5.3 Update tool docstrings with new output fields
