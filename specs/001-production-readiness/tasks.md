# Tasks: Production Readiness Remediation

**Input**: Design documents from `/specs/001-production-readiness/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are MANDATORY per spec success criteria SC-020 through SC-022:
- SC-020: Achieve test pyramid targets (70% unit, 20% integration, 10% e2e)
- SC-021: 100% functional requirement coverage (all 30 FR requirements)
- SC-022: Comprehensive security test suite

**Organization**: Tasks grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project structure - all paths relative to repository root:
- `src/` - Core implementation
- `tests/` - Test suite
- `server.py` - MCP server entry point

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and verification

- [X] T001 Verify Python 3.10+ environment and dependencies (FastMCP, Pydantic 2.0+, PyYAML)
- [X] T002 [P] Review existing test baseline (125 tests: 18% unit, 75% integration, 6% e2e)
- [X] T003 [P] Verify project structure matches plan.md expectations

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create file locking utility in src/utils.py with cross-platform support (fcntl/msvcrt)
- [X] T005 [P] Create error formatting utility in src/utils.py for stderr logging
- [X] T006 [P] Create path validation utility in src/utils.py for boundary checking
- [X] T007 [P] Create resource limit enforcement utilities in src/utils.py
- [X] T008 Add response size enforcement wrapper in src/utils.py (25K char limit)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 3 - Protect Credential Secrets (Priority: P1) 🎯 CRITICAL SECURITY

**Goal**: Remove exposed API key from version control and prevent future credential exposure

**Independent Test**: Scan repository for plaintext credentials and verify .gitignore exclusions work

### Implementation for User Story 3

- [X] T009 [US3] Remove OPENROUTER_API_KEY from .mcp.json (FR-004, FR-005)
- [X] T010 [US3] Add .mcp.json and .env to .gitignore
- [X] T011 [P] [US3] Create .env.template with credential documentation
- [X] T012 [US3] Verify git history no longer tracks .mcp.json with secrets
- [X] T013 [US3] Commit credential removal immediately (git add .gitignore .env.template)

### Tests for User Story 3

- [X] T014 [P] [US3] Unit test for credential scanning utility in tests/unit/test_security.py
- [X] T015 [P] [US3] Integration test verifying .gitignore excludes sensitive files in tests/integration/test_security.py

**Checkpoint**: No credentials exposed in version control (SC-003, SC-004)

---

## Phase 4: User Story 2 - Prevent Command Injection (Priority: P1) 🎯 CRITICAL SECURITY

**Goal**: Validate git commit hashes and prevent subprocess command injection

**Independent Test**: Provide malicious commit hashes and verify rejection before subprocess execution

### Implementation for User Story 2

- [X] T016 [US2] Add commit hash field validator to MapChangesInput in src/models.py (FR-002)
- [X] T017 [P] [US2] Update git subprocess calls to use array form in src/tools/changes.py
- [X] T018 [P] [US2] Add git binary availability check in src/tools/changes.py with clear error message
- [X] T019 [US2] Ensure all git operations have 30-second timeout in src/tools/changes.py

### Tests for User Story 2

- [X] T020 [P] [US2] Unit test for commit hash validator in tests/unit/test_validators.py
- [X] T021 [P] [US2] Unit test for git command construction in tests/unit/test_changes.py
- [X] T022 [US2] Integration test with shell metacharacters in commit hash in tests/integration/test_changes.py
- [X] T023 [US2] Integration test for missing git binary failure mode in tests/integration/test_changes.py

**Checkpoint**: 100% of malformed commit hashes rejected (SC-002)

---

## Phase 5: User Story 1 - Secure File System Operations (Priority: P1) 🎯 CRITICAL SECURITY

**Goal**: Prevent path traversal and symlink attacks across all file operations

**Independent Test**: Attempt to access files outside project boundary via path traversal and symlinks

### Implementation for User Story 1

- [X] T024 [P] [US1] Add project_path field validator to InitializeConfigInput in src/models.py (FR-001, FR-006)
- [X] T025 [P] [US1] Add docs_path field validator to InitializeConfigInput in src/models.py (FR-001)
- [X] T026 [US1] Implement path boundary check after resolution in src/tools/validation.py (FR-025)
- [X] T027 [US1] Add symlink detection before resolution in src/tools/validation.py (FR-003, FR-028)
- [X] T028 [P] [US1] Add symlink checks to file traversal in src/tools/memory.py (FR-028)
- [X] T029 [P] [US1] Add symlink checks to file traversal in src/tools/changes.py (FR-028)
- [X] T030 [P] [US1] Add symlink checks to file traversal in src/tools/dependencies.py (FR-028)

### Tests for User Story 1

- [X] T031 [P] [US1] Unit test for path traversal validator in tests/unit/test_validators.py
- [X] T032 [P] [US1] Unit test for path boundary utility in tests/unit/test_utils.py
- [X] T033 [P] [US1] Integration test with ../../../etc/passwd in link validation in tests/integration/test_validation.py
- [X] T034 [P] [US1] Integration test with symlink escaping project boundary in tests/integration/test_validation.py
- [X] T035 [US1] E2E test creating malicious symlinks in test project in tests/test_e2e_security.py

**Checkpoint**: 100% of path traversal attacks rejected (SC-001, SC-005)

---

## Phase 6: User Story 5 - Comprehensive Input Validation (Priority: P2)

**Goal**: Add Pydantic field validators for all input parameters to prevent injection and undefined behavior

**Independent Test**: Provide edge case inputs (empty, extreme lengths, special chars) and verify validation errors

### Implementation for User Story 5

- [x] T036 [P] [US5] Add exclude_patterns validator to InitializeConfigInput in src/models.py (FR-007)
- [x] T037 [P] [US5] Add sources validator to InitializeConfigInput in src/models.py (FR-007)
- [x] T038 [P] [US5] Add pattern length validators to all list fields in src/models.py (FR-006, FR-007)
- [x] T039 [US5] Add glob pattern syntax validation to prevent ReDoS in src/models.py (FR-008)
- [x] T040 [P] [US5] Add field validators for all optional fields to handle None gracefully in src/models.py
- [x] T041 [US5] Verify all tool parameter names match Pydantic model field names in src/tools/workflows.py (FR-014, FR-024)

### Tests for User Story 5

- [x] T042 [P] [US5] Unit test for exclude_patterns validator (max 50 items) in tests/unit/test_validators.py
- [x] T043 [P] [US5] Unit test for pattern item length validator (max 512 chars) in tests/unit/test_validators.py
- [x] T044 [P] [US5] Unit test for ReDoS pattern detection in tests/unit/test_validators.py
- [x] T045 [US5] Integration test with None/empty values for optional fields in tests/integration/test_models.py
- [x] T046 [US5] Integration test for workflows.py parameter name correctness in tests/integration/test_workflows.py

**Checkpoint**: All inputs validated (SC-011, SC-012, SC-013)

---

## Phase 7: User Story 4 - Correct MCP Protocol Implementation (Priority: P2)

**Goal**: Fix tool hints and enforce MCP response requirements

**Independent Test**: Invoke all tools and verify hints match behavior, responses within limits, valid JSON/markdown

### Implementation for User Story 4

- [x] T047 [US4] Fix readOnlyHint for docmgr_map_changes in server.py (currently True, should be False) (FR-009)
- [x] T048 [US4] Fix readOnlyHint for docmgr_track_dependencies in server.py (currently True, should be False) (FR-009)
- [x] T049 [P] [US4] Add response size enforcement to all tool wrappers using utility from T008 (FR-010)
- [x] T050 [P] [US4] Add JSON serialization error handling to all tools returning JSON in src/tools/*.py (FR-012)
- [x] T051 [US4] Remove unicode/emoji from JSON responses in src/tools/*.py (FR-011)
- [x] T052 [US4] Ensure all tools return strings on error (not raise to MCP layer) in src/tools/*.py (FR-013)

### Tests for User Story 4

- [x] T053 [P] [US4] Integration test verifying readOnlyHint accuracy for all 10 tools in tests/integration/test_server.py
- [x] T054 [P] [US4] Integration test for response size limit enforcement in tests/integration/test_protocol.py
- [x] T055 [P] [US4] Unit test for JSON serialization error handling in tests/unit/test_utils.py
- [x] T056 [US4] Integration test with large dependency graph triggering truncation in tests/integration/test_dependencies.py

**Checkpoint**: MCP protocol compliance (SC-006, SC-007, SC-008, SC-009, SC-010)

---

## Phase 8: User Story 6 - Graceful Error Handling (Priority: P3)

**Goal**: Replace all silent error handlers with proper logging and user-facing error messages

**Independent Test**: Trigger error conditions and verify helpful messages without sensitive data leaks

### Implementation for User Story 6

- [x] T057 [US6] Replace silent error handler in src/tools/config.py with stderr logging (FR-015)
- [x] T058 [P] [US6] Replace silent error handlers in src/tools/memory.py with stderr logging (FR-015)
- [x] T059 [P] [US6] Replace silent error handlers in src/tools/platform.py with stderr logging (FR-015)
- [x] T060 [P] [US6] Replace silent error handlers in src/tools/validation.py with stderr logging (FR-015)
- [x] T061 [P] [US6] Replace silent error handlers in src/tools/quality.py with stderr logging (FR-015)
- [x] T062 [P] [US6] Replace silent error handlers in src/tools/changes.py with stderr logging (FR-015)
- [x] T063 [P] [US6] Replace silent error handlers in src/tools/dependencies.py with stderr logging (FR-015)
- [x] T064 [P] [US6] Replace silent error handlers in src/tools/workflows.py with stderr logging (FR-015)
- [x] T065 [US6] Implement file locking for .doc-manager/repo-baseline.json in src/tools/memory.py (FR-018)
- [x] T066 [US6] Implement file locking for .doc-manager/dependencies.json in src/tools/dependencies.py (FR-018)
- [x] T067 [US6] Sanitize error messages to remove full paths in src/utils.py error formatter (FR-017)
- [x] T068 [US6] Add actionable guidance to all error messages in src/tools/*.py (FR-016)

### Tests for User Story 6

- [x] T069 [P] [US6] Unit test for error message sanitization in tests/unit/test_utils.py
- [x] T070 [P] [US6] Integration test for file lock timeout behavior in tests/integration/test_utils.py
- [x] T071 [P] [US6] Integration test for concurrent file modification with locks in tests/integration/test_concurrency.py
- [x] T072 [US6] E2E test for error message content (no paths, stack traces) in tests/test_e2e.py

**Checkpoint**: Zero silent failures, actionable errors (SC-014, SC-015, SC-016)

---

## Phase 9: User Story 7 - Resource Exhaustion Protection (Priority: P3)

**Goal**: Enforce file count, recursion depth, and timeout limits to prevent DoS

**Independent Test**: Process large projects and verify limits prevent resource exhaustion

### Implementation for User Story 7

- [x] T073 [P] [US7] Add file count limit (10K) to src/tools/memory.py file traversal (FR-019)
- [x] T074 [P] [US7] Add file count limit (10K) to src/tools/changes.py file traversal (FR-019)
- [x] T075 [P] [US7] Add file count limit (10K) to src/tools/dependencies.py file traversal (FR-019)
- [x] T076 [P] [US7] Add file count limit (10K) to src/tools/validation.py file traversal (FR-019)
- [x] T077 [P] [US7] Add 60-second timeout to src/tools/memory.py operations (FR-021)
- [x] T078 [P] [US7] Add 60-second timeout to src/tools/changes.py operations (FR-021)
- [x] T079 [P] [US7] Add 60-second timeout to src/tools/dependencies.py operations (FR-021)
- [x] T080 [P] [US7] Add 60-second timeout to src/tools/validation.py operations (FR-021)
- [ ] T081 [P] [US7] Add recursion depth limit (100) to src/tools/validation.py (FR-020)
- [ ] T082 [US7] Move regex compilation outside loop in src/tools/dependencies.py (FR-023)
- [ ] T083 [US7] Verify streaming/bounded memory in all file processing loops (FR-022)

### Tests for User Story 7

- [ ] T084 [P] [US7] Unit test for file count limit enforcement in tests/unit/test_utils.py
- [ ] T085 [P] [US7] Unit test for timeout enforcement in tests/unit/test_utils.py
- [ ] T086 [P] [US7] Integration test with 10K+ file project in tests/integration/test_limits.py
- [ ] T087 [US7] Integration test for operation timeout triggering in tests/integration/test_limits.py
- [ ] T088 [US7] E2E stress test with 100 concurrent tool invocations in tests/test_e2e_stress.py

**Checkpoint**: Resource limits enforced (SC-017, SC-018, SC-019, SC-023, SC-024, SC-025)

---

## Phase 10: Additional Bug Fixes (Cross-Cutting)

**Purpose**: Fix remaining implementation bugs not covered by user stories

- [ ] T089 [P] Fix line number off-by-one errors in src/tools/validation.py (FR-029)
- [ ] T090 [P] Fix quality score silent defaults in src/tools/quality.py (FR-030)
- [ ] T091 [P] Fix substring matching false positives in src/tools/dependencies.py (FR-026)
- [ ] T092 [P] Ensure exclude_patterns respected in src/tools/memory.py (FR-027)
- [ ] T093 [P] Ensure exclude_patterns respected in src/tools/changes.py (FR-027)

**Tests for Additional Bug Fixes**

- [ ] T094 [P] Integration test for accurate line numbers in validation reports in tests/integration/test_validation.py
- [ ] T095 [P] Integration test for quality score edge cases in tests/integration/test_quality.py
- [ ] T096 [P] Integration test for precise dependency matching in tests/integration/test_dependencies.py

---

## Phase 11: Polish & Verification

**Purpose**: Final validation and documentation

- [ ] T097 Run full test suite and verify all 125+ existing tests still pass
- [ ] T098 Verify new test pyramid distribution (target: 70% unit, 20% integration, 10% e2e)
- [ ] T099 [P] Update test-registry.json with all new tests
- [ ] T100 [P] Verify all 25 success criteria are met (SC-001 through SC-025)
- [ ] T101 Run quickstart.md validation checklist
- [ ] T102 Final commit with comprehensive message referencing all user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-9)**: All depend on Foundational phase completion
  - P1 stories (US3, US2, US1) should be completed first (critical security)
  - P2 stories (US5, US4) can proceed after P1 or in parallel if staffed
  - P3 stories (US6, US7) can proceed after P2 or in parallel if staffed
- **Bug Fixes (Phase 10)**: Can proceed in parallel with user stories
- **Polish (Phase 11)**: Depends on all user stories and bug fixes being complete

### User Story Dependencies

- **US3 (Credential Secrets)**: Can start after Foundational - No dependencies on other stories
- **US2 (Command Injection)**: Can start after Foundational - No dependencies on other stories
- **US1 (File System Security)**: Can start after Foundational - No dependencies on other stories
- **US5 (Input Validation)**: Can start after Foundational - Independent of other stories
- **US4 (MCP Compliance)**: Can start after Foundational - Independent of other stories
- **US6 (Error Handling)**: Can start after Foundational - Uses file locking utility from Foundational
- **US7 (Resource Limits)**: Can start after Foundational - Uses limit utilities from Foundational

### Within Each User Story

- Tests (if included) SHOULD be written and FAIL before implementation (TDD)
- Implementation tasks before integration tasks
- All tasks within story complete before moving to next priority

### Parallel Opportunities

- All Foundational tasks marked [P] can run in parallel (T004-T008)
- Within US3: T011 can run in parallel with T010
- Within US1: T024-T025 can run in parallel, T028-T030 can run in parallel
- Within US5: T036-T040 can run in parallel
- Within US4: T049-T051 can run in parallel
- Within US6: T058-T064 can run in parallel (different files)
- Within US7: T073-T076 can run in parallel, T077-T080 can run in parallel
- Phase 10 bug fixes can all run in parallel (T089-T093)

---

## Parallel Example: User Story 1

```bash
# Launch validation tasks together (different files, no dependencies):
Task T024: "Add project_path validator to src/models.py"
Task T025: "Add docs_path validator to src/models.py"

# Then launch symlink checks across multiple tools:
Task T028: "Add symlink checks to src/tools/memory.py"
Task T029: "Add symlink checks to src/tools/changes.py"
Task T030: "Add symlink checks to src/tools/dependencies.py"

# Launch all unit tests together:
Task T031: "Unit test for path traversal validator"
Task T032: "Unit test for path boundary utility"
```

---

## Parallel Example: User Story 6

```bash
# Launch error handler replacements across all 8 tool files:
Task T057: "Replace silent handlers in src/tools/config.py"
Task T058: "Replace silent handlers in src/tools/memory.py"
Task T059: "Replace silent handlers in src/tools/platform.py"
Task T060: "Replace silent handlers in src/tools/validation.py"
Task T061: "Replace silent handlers in src/tools/quality.py"
Task T062: "Replace silent handlers in src/tools/changes.py"
Task T063: "Replace silent handlers in src/tools/dependencies.py"
Task T064: "Replace silent handlers in src/tools/workflows.py"
```

---

## Implementation Strategy

### MVP First (P1 User Stories Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: US3 (Credential Secrets)
4. Complete Phase 4: US2 (Command Injection)
5. Complete Phase 5: US1 (File System Security)
6. **STOP and VALIDATE**: Test all P1 security fixes independently
7. Deploy/commit if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US3 (Credentials) → Test independently → Commit
3. Add US2 (Command Injection) → Test independently → Commit
4. Add US1 (Path Traversal) → Test independently → Commit (P1 complete!)
5. Add US5 (Input Validation) → Test independently → Commit
6. Add US4 (MCP Compliance) → Test independently → Commit (P2 complete!)
7. Add US6 (Error Handling) → Test independently → Commit
8. Add US7 (Resource Limits) → Test independently → Commit (P3 complete!)
9. Each story adds security/stability without breaking previous work

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US3 + US2 (credentials and command injection)
   - Developer B: US1 (path traversal - most complex)
   - Developer C: US5 (input validation)
3. Then proceed to P2/P3 stories in parallel
4. Stories complete and integrate independently

---

## Task Summary

**Total Tasks**: 102
- Setup: 3 tasks
- Foundational: 5 tasks (BLOCKS all user stories)
- US3 (Credential Secrets): 7 tasks (5 implementation + 2 tests)
- US2 (Command Injection): 8 tasks (4 implementation + 4 tests)
- US1 (File System Security): 12 tasks (7 implementation + 5 tests)
- US5 (Input Validation): 11 tasks (6 implementation + 5 tests)
- US4 (MCP Compliance): 10 tasks (6 implementation + 4 tests)
- US6 (Error Handling): 16 tasks (12 implementation + 4 tests)
- US7 (Resource Exhaustion): 16 tasks (11 implementation + 5 tests)
- Bug Fixes: 8 tasks (5 implementation + 3 tests)
- Polish: 6 tasks

**Parallel Opportunities**: 45 tasks marked [P] can run in parallel within their phase

**Test Distribution** (40 new tests):
- Unit: ~28 tests (70%)
- Integration: ~8 tests (20%)
- E2E: ~4 tests (10%)

**Independent Test Criteria**:
- US3: Repository scan finds zero credentials
- US2: Shell metacharacters in commit hash rejected
- US1: Path traversal attempts blocked
- US5: Edge case inputs handled gracefully
- US4: Tool hints accurate, responses within limits
- US6: Errors logged, no silent failures
- US7: Large projects respect limits

**MVP Scope**: US3 + US2 + US1 (all P1 security fixes) = Tasks T009-T035 (27 tasks)

---

## Notes

- [P] tasks = different files or independent operations, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD approach: Write tests first, ensure they fail, then implement
- Commit after each user story completion
- Stop at any checkpoint to validate story independently
- All 125 existing tests must continue to pass
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
