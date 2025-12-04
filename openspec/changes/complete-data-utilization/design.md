# Design: Complete Data Utilization

## Context

The v1.2.0 release partially addressed data utilization issues but left significant gaps:

1. **repo-baseline.json**: 6 of 10 fields stored but never read
2. **dependencies.json**: 3 of 6 sections computed but never consumed
3. **symbol-baseline.json**: 3 fields per symbol stored but ignored in comparisons

This represents wasted computation, storage, and user confusion ("why is this data here if nothing uses it?").

## Goals / Non-Goals

**Goals:**
- Every field stored in baseline files has at least one consumer
- No computed data is discarded unused
- Users understand what each field provides

**Non-Goals:**
- Adding new fields to baselines
- Changing baseline file formats
- Breaking existing tool outputs

## Decisions

### Decision 1: Create `load_repo_baseline()` helper

**What**: Add a dedicated loader function similar to `load_dependencies()` added in v1.2.0.

**Why**: Consistent pattern, schema validation, single point of loading.

**Location**: `doc_manager_mcp/tools/_internal/baselines.py` (new file)

### Decision 2: Stale reference warnings as validation issue type

**What**: Add `unmatched_references` to `docmgr_validate_docs` output as a new issue category.

**Why**: These are documentation quality issues - references to code that doesn't exist.

**Format**:
```json
{
  "type": "stale_reference",
  "reference": "docmgr_init()",
  "doc_file": "getting-started/quick-start.md",
  "severity": "warning"
}
```

### Decision 3: Parent/doc changes as semantic change types

**What**: Extend `SemanticChange.change_type` to include `parent_changed` and `doc_changed`.

**Why**: These are meaningful API changes:
- `parent_changed`: Symbol moved between classes (refactoring indicator)
- `doc_changed`: Docstring modified (documentation needs sync)

**Alternatives considered**:
- Separate from semantic changes → Rejected: These ARE semantic changes
- Combine with `modified` → Rejected: Loses specificity

### Decision 4: Docstring coverage as quality metric

**What**: Add "docstring_coverage" to `docmgr_assess_quality` output.

**Why**: "What percentage of public symbols have documentation?" is a fundamental quality metric.

**Formula**: `symbols_with_doc / total_public_symbols * 100`

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| External asset checking is slow | Default `check_external_assets=false`, opt-in |
| Stale reference noise from valid patterns | Allow filtering by reference type |
| Parent change detection false positives | Only flag if parent name differs, not None→value |

## Migration Plan

1. All changes are additive - no migration needed
2. New output fields have sensible defaults
3. Existing tool calls continue to work unchanged

## Open Questions

1. Should `doc_changed` severity be "breaking" or "non-breaking"?
   - Proposal: "non-breaking" since it doesn't affect runtime behavior

2. Should stale references block quality "good" rating?
   - Proposal: No, treat as informational warning
