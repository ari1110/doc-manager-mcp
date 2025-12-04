# Change: Complete Data Utilization Across All Baselines

## Why

The v1.2.0 release claimed to address "62% data waste" across baseline files but only implemented partial fixes. Currently:

- **repo-baseline.json**: 4/10 fields used (40%)
- **symbol-baseline.json**: 6/14 fields used (43%)
- **dependencies.json**: 2/6 sections used (33%)

Computed data that is never consumed represents wasted CPU cycles, disk space, and misleading capability suggestions. This change completes the remediation by ensuring every stored field has a concrete consumer.

## What Changes

### repo-baseline.json (6 unused fields → 0)

| Field | New Usage |
|-------|-----------|
| `repo_name` | Output headers, project filtering, sync reports |
| `description` | Quality reports, sync summaries |
| `language` | Language-specific validation rules |
| `docs_exist` | Early exit when no docs present |
| `version` | Schema version validation on load |
| `file_count` | Change percentage calculations |

### dependencies.json (3 unused sections → 0)

| Section | New Usage |
|---------|-----------|
| `doc_to_code` | "What code does this doc reference?" in validate/quality |
| `unmatched_references` | Stale reference warnings in validate_docs |
| `asset_to_docs` | Broken asset detection in validate_docs |

### symbol-baseline.json (3 unused fields → 0)

| Field | New Usage |
|-------|-----------|
| `column` | Precise location in action items |
| `parent` | Detect class hierarchy changes |
| `doc` | Docstring change detection, doc coverage metrics |

## Impact

- **Affected code**:
  - `doc_manager_mcp/tools/analysis/detect_changes.py`
  - `doc_manager_mcp/tools/analysis/validation/validator.py`
  - `doc_manager_mcp/tools/analysis/quality/*.py`
  - `doc_manager_mcp/tools/workflows/sync.py`
  - `doc_manager_mcp/core/actions.py`
  - `doc_manager_mcp/indexing/analysis/semantic_diff.py`

- **Affected tools**:
  - `docmgr_detect_changes` - Enhanced output with file_count percentage
  - `docmgr_validate_docs` - New stale reference and broken asset warnings
  - `docmgr_assess_quality` - Docstring coverage metric
  - `docmgr_sync` - Enhanced summary with repo metadata

- **Breaking changes**: None (additive only)
