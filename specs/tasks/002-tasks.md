# Tasks: Tool Architecture Refactoring (002)

## Phase 1: Branch Setup & Foundation

### T001: Create Feature Branch ✅
- Branch name: `refactor/7-tools`
- Status: **Completed**

### T002: Create Spec Documentation ✅
- File: `specs/002-tool-architecture-refactor.md`
- File: `specs/tasks/002-tasks.md`
- Status: **Completed**

**Commit:** `docs: create spec for tool architecture refactor (002)`

---

## Phase 2: Model Updates

### T003: Add `DocmgrInitInput` Model
**File:** `doc_manager_mcp/models.py`
**Fields:**
- project_path: str
- mode: "existing" | "bootstrap" (default: "existing")
- platform: DocumentationPlatform | None
- exclude_patterns: list[str] | None
- docs_path: str | None
- sources: list[str] | None

### T004: Add `DocmgrDetectChangesInput` Model
**File:** `doc_manager_mcp/models.py`
**Fields:**
- project_path: str
- since_commit: str | None
- mode: ChangeDetectionMode (default: CHECKSUM)
- include_semantic: bool (default: False)

### T005: Add `DocmgrUpdateBaselineInput` Model
**File:** `doc_manager_mcp/models.py`
**Fields:**
- project_path: str
- docs_path: str | None

### T006: Update `SyncInput` Model
**File:** `doc_manager_mcp/models.py`
**Changes:**
- mode: "check" | "resync" (default: "check")
- Remove old "reactive"/"proactive" modes

**Commit:** `feat: add input models for refactored tools (T003-T006)`

---

## Phase 3: New Tool Implementations

### T007: Create `tools/init.py`
**Function:** `docmgr_init(params, ctx)`
**Logic:**
- If mode="existing": initialize_config + initialize_memory + track_dependencies
- If mode="bootstrap": bootstrap workflow + track_dependencies
- Return comprehensive initialization report

### T008: Create `tools/detect_changes.py`
**Function:** `docmgr_detect_changes(params)`
**KEY REQUIREMENT:** Pure read-only (NEVER writes symbol-baseline.json)
**Logic:**
- Reuse existing change detection logic
- Skip all baseline writes
- Return change report only

### T009: Create `tools/update_baseline.py`
**Function:** `docmgr_update_baseline(params, ctx)`
**Updates:** repo-baseline.json + symbol-baseline.json + dependencies.json
**Helper functions:**
- _update_repo_baseline()
- _update_symbol_baseline()

### T010: Update `tools/workflows.py`
**Function:** Modify `sync()`
**Changes:**
- Add mode parameter handling
- mode="check": Call docmgr_detect_changes (read-only)
- mode="resync": Call docmgr_update_baseline first, then detect_changes

**Commit:** `feat: implement Tier 1-3 refactored tools (T007-T010)`

---

## Phase 4: Server Registration & Deprecation

### T011: Register New Tools in `server.py`
**Add:**
- @mcp.tool for docmgr_init (readOnlyHint=False)
- @mcp.tool for docmgr_detect_changes (readOnlyHint=True)
- @mcp.tool for docmgr_update_baseline (readOnlyHint=False)

### T012: Update Existing Tool Annotations
**Changes:**
- docmgr_sync: readOnlyHint=False (mode="resync" writes)
- Rename docmgr_validate_docs → docmgr_validate
- Update sync parameter: mode default to "check"

### T013: Add Deprecation Warnings
**Tools to deprecate:**
- docmgr_initialize_config → "[DEPRECATED] Use docmgr_init"
- docmgr_initialize_memory → "[DEPRECATED] Use docmgr_init"
- docmgr_bootstrap → "[DEPRECATED] Use docmgr_init mode='bootstrap'"
- docmgr_map_changes → "[DEPRECATED] Use docmgr_detect_changes or docmgr_update_baseline"
- Keep tools functional with warning in output

**Commit:** `feat: register new tools and deprecate old tools (T011-T013)`

---

## Phase 5: Testing & Validation

### T014: Create Unit Tests
**Files:**
- `tests/test_init.py`: Both modes, dependency tracking, errors
- `tests/test_detect_changes.py`: Verify no writes, both modes
- `tests/test_update_baseline.py`: Atomic updates, file locking

### T015: Update Integration Tests
**File:** `tests/test_integration.py`
**Tests:**
- Full workflow with new tools
- Backward compatibility (old tools)
- Migration test (old → new API)

**Commit:** `test: add comprehensive tests for refactored tools (T014-T015)`

---

## Phase 6: Documentation

### T016: Update `README.md`
**Add:**
- Tool architecture diagram (7 tools in tiers)
- Tool descriptions
- Quick start examples

### T017: Create Migration Guide
**File:** `docs/migration/001-to-002.md`
**Content:**
- Tool mapping table (old → new)
- Code examples (before/after)
- Deprecation timeline

### T018: Update API Reference
**Add:**
- Full docs for 7 tools
- Mode parameter explanations
- Workflow examples

**Commit:** `docs: update documentation for tool refactor (T016-T018)`

---

## Phase 7: Final Validation & Cleanup

### T019: Run Full Test Suite
**Command:** `pytest tests/ -v --cov=doc_manager_mcp`
**Acceptance:** All tests passing, coverage ≥ 85%

### T020: Manual Integration Testing
**Tests:**
- Fresh project init (mode="existing")
- Bootstrap new docs (mode="bootstrap")
- Detect changes (verify read-only)
- Update baselines (verify all 3 files)
- Sync both modes
- Old tools with warnings

### T021: Update Version & Changelog
**Files:**
- `pyproject.toml`: version = "1.1.0"
- `CHANGELOG.md`: Added/Changed/Deprecated sections

**Commit:** `chore: bump version to 1.1.0 and update changelog (T021)`

---

## Phase 8: Merge & Release

### T022: Create Pull Request
- Push branch refactor/7-tools
- PR description with tool mapping

### T023: Code Review
- Address feedback
- Update tests/docs

### T024: Merge to Main
- Merge refactor/7-tools → main
- Tag v1.1.0
- Push with tags

---

## Summary

**Total Tasks:** 24 (T001-T024)
**New Files:** 6 (init.py, detect_changes.py, update_baseline.py, 3 test files, migration guide)
**Modified Files:** 4 (models.py, workflows.py, server.py, README.md)
**Estimated Timeline:** 3-5 days
