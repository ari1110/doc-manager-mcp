# Quickstart: Production Readiness Remediation

**Feature**: MCP Server Production Readiness
**Date**: 2025-11-15
**Branch**: `001-production-readiness`

## Overview

This guide helps developers quickly implement the production readiness remediation for the doc-manager MCP server. Follow these steps in order to systematically address all 30 functional requirements across 7 user stories.

## Prerequisites

- Python 3.10+
- Git installed and in PATH
- Existing doc-manager MCP server codebase
- pytest, pytest-asyncio, pytest-cov installed

## Priority Order (Based on User Stories)

### P1 - Critical Security (MUST FIX FIRST)

1. **US1**: Secure File System Operations
2. **US2**: Prevent Command Injection
3. **US3**: Protect Credential Secrets

### P2 - MCP Compliance (HIGH PRIORITY)

4. **US4**: Correct MCP Protocol Implementation
5. **US5**: Comprehensive Input Validation

### P3 - Robustness (MEDIUM PRIORITY)

6. **US6**: Graceful Error Handling
7. **US7**: Resource Exhaustion Protection

## Phase-by-Phase Implementation

### Phase 0: Immediate Security Fix (5 minutes)

**Critical**: Remove exposed API key BEFORE any other work

```bash
# 1. Remove API key from .mcp.json
# Edit .mcp.json and delete the OPENROUTER_API_KEY line

# 2. Add to .gitignore
echo ".mcp.json" >> .gitignore
echo ".env" >> .gitignore

# 3. Create environment variable template
cat > .env.template <<EOF
# MCP Server Configuration
# Copy this to .mcp.json and replace with actual values
OPENROUTER_API_KEY=your-api-key-here
EOF

# 4. Commit immediately
git add .gitignore .env.template
git commit -m "fix: remove exposed API key, add to gitignore

Critical security fix: Remove hardcoded API key from version control.

- Delete OPENROUTER_API_KEY from .mcp.json
- Add .mcp.json and .env to .gitignore
- Create .env.template for documentation

FR-004, FR-005

Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Verify**: Check that `git log --all -- .mcp.json` shows the file is no longer tracked with secrets.

---

### Phase 1: Input Validation (src/models.py)

**Goal**: Add Pydantic field validators to prevent path traversal and command injection

**Files**: `src/models.py`

**Steps**:

1. **Add path validation** (FR-001, FR-006):

```python
from pydantic import field_validator
import re

class InitializeConfigInput(BaseModel):
    # ... existing fields ...

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v):
        if '..' in v:
            raise ValueError('Path traversal sequences (..) not allowed')
        if len(v) > 260:
            raise ValueError('Path exceeds maximum length (260 characters)')
        # Additional validation...
        return v
```

2. **Add commit hash validation** (FR-002):

```python
class MapChangesInput(BaseModel):
    # ... existing fields ...

    @field_validator('since_commit')
    @classmethod
    def validate_commit_hash(cls, v):
        if v is None:
            return v
        if not re.match(r'^[0-9a-fA-F]{7,40}$', v):
            raise ValueError('Invalid git commit hash format')
        return v
```

3. **Add list constraints** (FR-007):

```python
@field_validator('exclude_patterns')
@classmethod
def validate_patterns(cls, v):
    if v and len(v) > 50:
        raise ValueError('Maximum 50 exclude patterns allowed')
    for pattern in (v or []):
        if len(pattern) > 512:
            raise ValueError(f'Pattern exceeds 512 characters')
    return v
```

**Test**:
```bash
# Create unit tests
pytest tests/unit/test_models.py -v
```

**Commit**:
```bash
git add src/models.py tests/unit/test_models.py
git commit -m "feat: add input validation to Pydantic models

Add field validators to prevent security vulnerabilities:
- Path traversal validation (no .. sequences)
- Commit hash format validation (7-40 hex chars)
- List length and item constraints (max 50 items, 512 chars each)

FR-001, FR-002, FR-006, FR-007

US5: Comprehensive Input Validation

Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Phase 2: Path Boundary Protection (src/tools/validation.py)

**Goal**: Fix path traversal vulnerability in link validation

**Files**: `src/tools/validation.py`

**Steps**:

1. **Add boundary check after path resolution** (FR-025):

```python
# validation.py:70-87 (approx)
def _check_broken_links(...):
    # ... existing code ...
    target = docs_root / url_without_anchor.lstrip('/')
    try:
        target = target.resolve()

        # ADD THIS: Verify resolved path stays within docs_root
        if not target.is_relative_to(docs_root):
            return f"Path traversal detected: {link_url} escapes documentation boundary"

        if not target.exists():
            return f"Broken link: {link_url}..."
```

2. **Add symlink detection** (FR-003, FR-028):

```python
# Before resolving, check if it's a symlink
if target.is_symlink():
    resolved_target = target.resolve()
    if not resolved_target.is_relative_to(docs_root):
        return f"Symlink escapes boundary: {link_url} points to {resolved_target}"
```

**Test**:
```bash
# Add path traversal tests
pytest tests/integration/test_validation.py::test_path_traversal -v
```

**Commit**: Follow commit message format (see Phase 1 example)

---

### Phase 3: Error Handling (src/tools/*.py)

**Goal**: Replace 22 silent error handlers with proper logging

**Files**: All 8 tool files in `src/tools/`

**Find silent failures**:
```bash
grep -n "except.*pass" src/tools/*.py
```

**Replace pattern**:
```python
# BEFORE (WRONG):
try:
    # operation
except Exception:
    pass  # Silent failure!

# AFTER (CORRECT):
try:
    # operation
except Exception as e:
    print(f"ERROR: Failed to process {item}: {e}", file=sys.stderr)
    # Decide: continue processing other items, or raise
```

**Per clarification**: Errors logged to stderr only (no log files)

**Commit**: One commit per tool file after fixing all silent failures in that file

---

### Phase 4: MCP Tool Hints (server.py)

**Goal**: Correct readOnlyHint for 2 tools

**Files**: `server.py`

**Change**:
```python
# BEFORE:
@mcp.tool(
    name="docmgr_map_changes",
    annotations={"readOnlyHint": True, ...}  # WRONG
)

# AFTER:
@mcp.tool(
    name="docmgr_map_changes",
    annotations={"readOnlyHint": False, ...}  # CORRECT (writes to .doc-manager/)
)

# Same for docmgr_track_dependencies
```

**Test**:
```bash
pytest tests/integration/ -k "test_map_changes or test_track_dependencies" -v
```

**Commit**: Single commit for both hint fixes (FR-009)

---

### Phase 5: File Locking (src/utils.py)

**Goal**: Implement cross-platform file locking with timeout/retry

**Files**: `src/utils.py`, all tools that modify `.doc-manager/`

**Implementation**:

1. **Add lock utility** (FR-018):

```python
import fcntl  # Unix
import msvcrt  # Windows
import platform
from contextlib import contextmanager

@contextmanager
def file_lock(file_path: Path, timeout: int = 5, retries: int = 3):
    """Acquire exclusive file lock with timeout and retry."""
    lock_file = file_path.with_suffix(file_path.suffix + '.lock')

    for attempt in range(retries):
        try:
            # Platform-specific lock acquisition
            if platform.system() == 'Windows':
                # msvcrt locking
                pass
            else:
                # fcntl locking
                pass

            yield  # Lock acquired, execute critical section

            # Release lock
            break
        except TimeoutError:
            if attempt == retries - 1:
                raise
            time.sleep(1)  # Wait before retry
```

2. **Use in tools**:

```python
# memory.py, changes.py, dependencies.py
with file_lock(baseline_path):
    # Read/write state file
    pass
```

**Test**: Concurrent access tests

**Commit**: Implement locking utility + update all tools using state files

---

### Phase 6: Resource Limits (src/tools/*.py)

**Goal**: Add file count, recursion depth, and timeout limits

**Files**: `memory.py`, `changes.py`, `dependencies.py`, `validation.py`

**Pattern**:
```python
import signal

def process_with_limits(project_path: Path):
    # Set timeout
    signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError()))
    signal.alarm(60)  # 60-second timeout

    try:
        file_count = 0
        for file_path in project_path.rglob("*"):
            if file_count >= 10000:  # FR-019
                raise ValueError("File count limit exceeded (10,000)")
            # Process file
            file_count += 1
    finally:
        signal.alarm(0)  # Cancel timeout
```

**Test**: Large project simulation tests

**Commit**: One commit per tool after adding limits

---

### Phase 7: Testing (tests/)

**Goal**: Add security tests for all attack vectors

**New test files**:
- `tests/unit/test_validators.py` - Field validator tests
- `tests/integration/test_security.py` - Security scenario tests
- `tests/test_e2e_security.py` - End-to-end attack tests

**Coverage targets** (SC-022):
- Path traversal attacks
- Command injection attempts
- Symlink attacks
- Credential exposure scans

**Run full test suite**:
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

**Verify pyramid** (SC-020):
```bash
.claude/skills/speckit/scripts/test-registry.sh export-for-plan --json
# Should show improved pyramid ratio
```

**Commit**: Test files as they're added

---

## Verification Checklist

Before marking remediation complete, verify ALL success criteria:

- [ ] SC-001: 100% path traversal attacks rejected
- [ ] SC-002: 100% malformed commit hashes rejected
- [ ] SC-003: Zero exposed credentials in tracked files
- [ ] SC-004: `.mcp.json` and `.env` in `.gitignore`
- [ ] SC-005: Symlinks detected in 100% of test cases
- [ ] SC-006: All readOnlyHint values accurate (0% mismatches)
- [ ] SC-007: 100% responses within 25,000 char limit
- [ ] SC-008: 100% valid JSON responses
- [ ] SC-009: Zero exceptions raised to MCP layer
- [ ] SC-010: Zero AttributeError from parameter mismatches
- [ ] SC-011: All path inputs validated (100% coverage)
- [ ] SC-012: All list parameters have constraints
- [ ] SC-013: Edge cases handled gracefully (100%)
- [ ] SC-014: Zero silent error handlers remain
- [ ] SC-015: 100% error messages actionable
- [ ] SC-016: Zero sensitive info in error messages
- [ ] SC-017: File count limits enforced
- [ ] SC-018: Timeouts enforced (100%)
- [ ] SC-019: Memory usage bounded
- [ ] SC-020: Test pyramid targets achieved
- [ ] SC-021: All 30 FR have test coverage
- [ ] SC-022: Security test suite comprehensive
- [ ] SC-023: 100 tool invocations without crashes
- [ ] SC-024: Concurrent calls complete without corruption
- [ ] SC-025: Performance targets met

## Common Pitfalls

1. **Don't skip the API key removal** - This is CRITICAL and must be done first
2. **Don't batch commits** - Commit after each user story/phase
3. **Don't modify tests and code in same commit** - Separate commits for testability
4. **Don't forget Windows compatibility** - File locking differs on Windows vs Unix
5. **Don't ignore existing tests** - All 125 existing tests must still pass

## Getting Help

- See `research.md` for technical design decisions
- See `data-model.md` for validation schema details
- See `plan.md` for constitution check and testing strategy
- See `spec.md` for complete requirements and acceptance criteria

## Next Steps After Quickstart

Once all phases complete:
1. Run full test suite
2. Verify all 25 success criteria
3. Update `test-registry.json`
4. Mark spec as "Complete"
5. Create PR for review
