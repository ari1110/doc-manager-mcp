# Spec: Tool Architecture Refactoring (002)

## Overview

Refactor doc-manager MCP server from 10 tools to 7 tools to eliminate overlaps, clarify responsibilities, and improve developer experience.

## Problem Statement

Current architecture has 10 tools with several issues:
1. **Initialization split**: `initialize_config` + `initialize_memory` are separate (unclear order)
2. **Bootstrap overlap**: `bootstrap` duplicates init tools functionality + creates docs
3. **sync marked read-only but writes**: Calls `map_changes` which writes `symbol-baseline.json`
4. **track_dependencies orphaned**: Not part of any workflow, users must remember to run it
5. **Unclear naming**: `map_changes` sounds read-only but modifies state

## Goals

1. Reduce tool count from 10 → 7 with clear organization
2. Eliminate hidden side effects (readOnlyHint must be accurate)
3. Make init comprehensive (include dependency tracking)
4. Separate read vs write operations explicitly
5. Maintain backward compatibility (old tools still work)

## Proposed Architecture

### Tier 1: Setup (1 tool)
**docmgr_init** - Unified initialization
- `mode="existing"`: Add tracking to existing project (config + baselines + dependencies)
- `mode="bootstrap"`: Create new docs from scratch (+ doc templates)
- **Replaces**: initialize_config, initialize_memory, bootstrap

### Tier 2: Read-Only Analysis (4 tools)
- **docmgr_detect_changes** - Pure read-only change detection (renamed from map_changes)
- **docmgr_validate** - Link/asset validation (renamed from validate_docs)
- **docmgr_assess_quality** - Quality scoring (unchanged)
- **docmgr_detect_platform** - Platform detection (unchanged)

### Tier 3: State Management (2 tools)
**docmgr_sync** - Comprehensive health check with modes
- `mode="check"`: Read-only analysis (safe for CI/CD)
- `mode="resync"`: Update all baselines + run analysis

**docmgr_update_baseline** - Explicit baseline refresh
- Updates: repo-baseline.json + symbol-baseline.json + dependencies.json
- Makes state changes explicit

### Tier 4: Workflows (1 tool)
- **docmgr_migrate** - Restructure docs (unchanged)

## Key Design Decisions

1. **Init includes dependency tracking**: Complete baseline snapshot from the start
2. **Sync uses mode parameter**: Single tool with `mode="check" | "resync"` instead of separate tools
3. **Update_baseline is comprehensive**: Updates all tracking files atomically
4. **Detect_changes is pure read-only**: No baseline writes whatsoever
5. **Backward compatibility**: Old tools deprecated but remain functional

## Implementation Phases

See `specs/tasks/002-tasks.md` for detailed task breakdown.

## Acceptance Criteria

- ✅ All 7 new tools implemented and tested
- ✅ Old tools deprecated but functional
- ✅ `docmgr_detect_changes` is pure read-only (no baseline writes)
- ✅ `docmgr_update_baseline` updates all 3 files atomically
- ✅ `docmgr_init` includes dependency tracking
- ✅ `docmgr_sync` modes are clear (check/resync)
- ✅ All readOnlyHint annotations are accurate
- ✅ Test coverage ≥ 85%
- ✅ Documentation complete (README, migration guide, API ref)

## Migration Strategy

### Phase 1: Add new tools (non-breaking)
Add new tools alongside existing ones

### Phase 2: Update existing tools
Rename and fix annotations

### Phase 3: Deprecate old tools
Mark as deprecated but keep functional

### Timeline
- Implementation: Tasks T001-T018
- Testing: Full test suite + manual integration
- Documentation: Migration guide + API reference
- Release: Version 1.1.0

## Success Metrics

1. **Developer Experience**: Single init entry point, clear tool responsibilities
2. **Clarity**: No hidden side effects, accurate readOnlyHint annotations
3. **Maintainability**: Reduced tool count, clearer code organization
4. **Backward Compatibility**: Existing users' code continues to work
