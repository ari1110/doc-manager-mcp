# Implementation Plan: MCP Server Production Readiness Remediation

**Branch**: `001-production-readiness` | **Date**: 2025-11-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-production-readiness/spec.md`

**Note**: This template is filled in by loading `references/speckit.plan.md`. See that file for the execution workflow.

## Summary

This plan addresses critical production readiness issues in the doc-manager MCP server identified through comprehensive security and compliance auditing. The remediation focuses on fixing 5 critical security vulnerabilities (path traversal, command injection, exposed credentials, symlink attacks, unbounded resource consumption), correcting MCP protocol compliance issues (incorrect tool hints, missing response size limits, improper error handling), and resolving 25+ implementation bugs across 8 tool modules. The technical approach leverages Pydantic 2.0 field validators for input validation, implements file locking with timeouts for concurrent access protection, adds stderr-based error logging, and enforces resource limits throughout the codebase while maintaining backward compatibility with existing MCP tool interfaces.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastMCP (mcp>=1.0.0), Pydantic 2.0+, PyYAML 6.0+
**Storage**: File system (.doc-manager/ directory for state, YAML configs)
**Testing**: pytest 7.0+, pytest-asyncio 0.21+, pytest-cov 4.0+ (125 existing tests)
**Target Platform**: Cross-platform (Windows, macOS, Linux) - MCP stdio server
**Project Type**: Single project (Python MCP server with async tools)
**Performance Goals**:
- Small projects (<1K files): <5s per tool invocation
- Medium projects (<10K files): <30s per tool invocation
- Large projects (10K files with limits): <60s per tool invocation
- Response size: ≤25,000 characters per MCP response

**Constraints**:
- Backward compatibility: No breaking changes to MCP tool interfaces
- Resource limits: Max 10,000 files processed, max 100 recursion depth
- File lock timeout: 5 seconds with 3 retries (total ~15s)
- Git operation timeout: 30 seconds
- No external network dependencies (local-only operations)

**Scale/Scope**:
- 10 MCP tools to remediate (8 with bugs, 2 with incorrect hints)
- 30 functional requirements to implement
- 8 source files to modify (src/tools/*.py, src/models.py, server.py)
- 125 existing tests to maintain, add security/validation tests
- 1 critical security issue (exposed API key) to resolve immediately

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**I. Accuracy and Transparency** ✅ PASS
- Spec explicitly lists 30 functional requirements with measurable criteria
- 25 success criteria define 100% coverage targets (no partial completion allowed)
- Out of scope section clearly defines what is NOT being fixed
- No shortcuts permitted: All 30 FR requirements must be implemented

**II. Specification Adherence** ✅ PASS
- Spec provides explicit requirements (FR-001 through FR-030) with no ambiguity
- 7 user stories with detailed acceptance scenarios
- Clarifications documented in spec (3 operational decisions captured)
- Implementation must follow spec exactly: No reinterpretation of security fixes

**III. Fail-Fast Error Handling** ✅ PASS (Primary Goal)
- FR-015: Replace ALL silent error handlers (`except: pass`) - 22 instances identified
- FR-016: Error messages must provide actionable guidance
- FR-017: Errors must not expose sensitive information
- This remediation directly enforces constitution principle III

**IV. Comprehensive Testing** ⚠️ CONDITIONAL
- Current: 125 tests (18% unit, 75% integration, 6% e2e) - INVERTED pyramid ❌
- Target: 70% unit, 20% integration, 10% e2e per SC-020
- Gate: Add security tests (path traversal, command injection, symlink attacks)
- Gate: Achieve 100% coverage of 30 functional requirements per SC-021
- **Action**: Security test suite MUST be added before marking complete

**V. Security First** ✅ PASS (Primary Goal)
- 8 security-focused functional requirements (FR-001 through FR-008)
- Path traversal protection, command injection prevention, credential protection
- Symlink attack prevention, input validation, ReDoS protection
- This remediation directly addresses OWASP Top 10 vulnerabilities

**VI. Frequent Commits** ✅ PASS
- Spec organized into 7 user stories (P1, P2, P3 priorities)
- Commit after each user story implementation
- Commit after each phase of spec
- Constitution-compliant commit message format required

**VII. Architectural Integrity** ✅ PASS
- No new layers introduced (remediation of existing structure)
- Changes constrained to: src/models.py (validators), src/tools/*.py (fixes), server.py (hints)
- Maintains existing separation: models → tools → server
- No circular dependencies introduced

**Overall Gate Status**: ✅ PASS with ACTION REQUIRED
- **Blocker**: None - all gates pass
- **Action Required**: Security test suite must be comprehensive (SC-022)
- **Re-check**: After Phase 1 design, verify no architecture violations

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (speckit.plan workflow output)
├── research.md          # Phase 0 output (speckit.plan workflow)
├── data-model.md        # Phase 1 output (speckit.plan workflow)
├── quickstart.md        # Phase 1 output (speckit.plan workflow)
├── contracts/           # Phase 1 output (speckit.plan workflow)
└── tasks.md             # Phase 2 output (speckit.tasks workflow - NOT created by speckit.plan)
```

### Source Code (repository root)

**Current Structure** (Single Python MCP Server Project):

```text
doc-manager/
├── server.py                    # MCP server entry point (MODIFY: fix readOnlyHint)
├── .gitignore                   # (MODIFY: add .mcp.json, .env)
├── .mcp.json                    # (DELETE KEY: remove exposed API key)
│
├── src/                         # Core implementation (MODIFY multiple files)
│   ├── __init__.py
│   ├── constants.py             # Enums and limits (NO CHANGES)
│   ├── models.py                # Pydantic input models (MODIFY: add validators)
│   ├── utils.py                 # Shared utilities (MODIFY: error handling, locks)
│   └── tools/                   # MCP tool implementations (MODIFY all 8 files)
│       ├── __init__.py
│       ├── config.py            # (MODIFY: race condition, validation)
│       ├── memory.py            # (MODIFY: exclude patterns, validation)
│       ├── platform.py          # (MODIFY: error handling)
│       ├── validation.py        # (MODIFY: path traversal, boundary checks)
│       ├── quality.py           # (MODIFY: error handling, scoring)
│       ├── changes.py           # (MODIFY: exclude patterns, validation)
│       ├── dependencies.py      # (MODIFY: performance, false positives)
│       └── workflows.py         # (MODIFY: parameter names, error handling)
│
├── tests/                       # Test suite (ADD security tests)
│   ├── unit/
│   │   └── test_utils.py        # (ADD: test new validators)
│   ├── integration/
│   │   ├── test_config.py       # (MODIFY: add validation tests)
│   │   ├── test_memory.py       # (MODIFY: add symlink tests)
│   │   ├── test_platform.py     # (MODIFY: git failure tests)
│   │   ├── test_validation.py   # (ADD: path traversal tests)
│   │   ├── test_quality.py      # (MODIFY: error handling tests)
│   │   ├── test_changes.py      # (ADD: commit hash validation tests)
│   │   ├── test_dependencies.py # (MODIFY: performance tests)
│   │   └── test_workflows.py    # (MODIFY: parameter name tests)
│   └── test_e2e.py              # (ADD: security scenarios)
│
└── test-registry.json           # Test metadata (UPDATE with new tests)
```

**Structure Decision**: Single project structure is appropriate for this MCP server. All changes are in-place modifications to existing files with no new directories or architectural changes. The remediation maintains the current modular separation: models (input validation) → tools (business logic) → server (MCP registration).

## Testing Strategy

**Coverage Baseline** (from `test-registry.sh export-for-plan --json`):
- Total tests: 125 | Unit: 23 (18%) | Integration: 94 (75%) | E2E: 8 (6%)
- Pyramid health: **WARN** (inverted pyramid - too many integration tests)
- Existing tests for this spec: None - new spec (remediation work)
- Retirement candidates: 0 tests (no deprecated features)

**Test Pyramid Targets** (per SC-020):
- Unit: ~70% (~87 tests total, add ~64 new unit tests)
- Integration: ~20% (~25 tests total, reduce by ~69 or refactor to unit)
- E2E: ~10% (~12 tests total, add ~4 new e2e tests)

**Note**: This remediation does NOT require full pyramid rebalancing (that's out of scope per spec). However, NEW tests added for this spec MUST follow 70/20/10 distribution to avoid worsening the pyramid.

**New Tests Required** (estimated ~40 new tests for this spec):
- Unit: ~28 tests (70% of new tests) - validator functions, error handlers, utility functions
- Integration: ~8 tests (20% of new tests) - tool-level security scenarios
- E2E: ~4 tests (10% of new tests) - end-to-end security attack scenarios

**Mocking Strategy**:
- **Unit Tests**: Mock all I/O (file system, subprocess, git commands)
- **Integration Tests**: Real file system with isolated tmp_path, mock external subprocess calls
- **E2E Tests**: Real file system, real git commands (requires git installed)

**Component Test Coverage**:

| Component/Module | Unit | Integration | E2E | Notes |
|------------------|------|-------------|-----|-------|
| src/models.py validators | Yes | No | No | Pure validation logic, mock-independent |
| src/utils.py locking | Yes | Yes | No | Unit test lock logic, integration test concurrent access |
| src/utils.py error handling | Yes | No | No | Test error formatting and stderr output |
| src/tools/validation.py | Yes | Yes | Yes | Unit: boundary checks, Integration: path traversal, E2E: symlink attacks |
| src/tools/changes.py | Yes | Yes | No | Unit: commit hash validation, Integration: git diff safety |
| src/tools/workflows.py | Yes | Yes | No | Unit: parameter mapping, Integration: AttributeError prevention |
| src/tools/memory.py | Yes | Yes | No | Unit: exclude patterns, Integration: file traversal with limits |
| src/tools/dependencies.py | Yes | Yes | No | Unit: regex matching, Integration: performance with 10K files |
| server.py hints | No | Yes | No | Integration tests verify correct readOnlyHint values |
| Security attack vectors | Yes | Yes | Yes | All layers: path traversal, command injection, symlinks |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**N/A** - No constitution violations identified. All gates pass. This remediation work aligns with constitution principles:
- Enforces fail-fast error handling (Principle III)
- Implements security-first approach (Principle V)
- Maintains architectural integrity (Principle VII)
- Requires comprehensive testing (Principle IV)
