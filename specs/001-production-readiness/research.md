# Research: Production Readiness Remediation

**Feature**: MCP Server Production Readiness
**Date**: 2025-11-15
**Phase**: Phase 0 - Research

## Overview

This document captures technical research and design decisions for remediating critical production readiness issues in the doc-manager MCP server. Since this is a remediation project fixing existing code rather than building new features, research focuses on best practices for security hardening, input validation, and error handling in Python MCP servers.

## Key Technical Decisions

### 1. Input Validation Approach

**Decision**: Use Pydantic v2 field validators with `@field_validator` decorator

**Rationale**:
- Already using Pydantic 2.0+ for input models
- Field validators provide declarative, reusable validation logic
- Integrates seamlessly with FastMCP's automatic schema generation
- Supports complex validation (path traversal checks, regex patterns)
- Clear error messages automatically generated

**Alternatives Considered**:
- Manual validation in tool functions: Rejected - duplicates code, harder to test
- Custom validator classes: Rejected - over-engineering for this use case
- Pre-validation middleware: Rejected - doesn't integrate with Pydantic models

**Implementation Pattern**:
```python
from pydantic import field_validator

class InitializeConfigInput(BaseModel):
    project_path: str = Field(..., min_length=1, max_length=260)

    @field_validator('project_path')
    @classmethod
    def validate_path(cls, v):
        if '..' in v:
            raise ValueError('Path traversal not allowed')
        # Additional checks...
        return v
```

### 2. File Locking Strategy

**Decision**: Use Python's `fcntl` (Unix) and `msvcrt` (Windows) with cross-platform wrapper

**Rationale**:
- Clarification answer: 5-second timeout with 3 retries
- Native OS-level locks prevent race conditions between concurrent MCP tool calls
- Required for `.doc-manager/` state files (repo-baseline.json, dependencies.json)
- Platform-specific but abstracted through utility function

**Alternatives Considered**:
- File-based semaphores: Rejected - doesn't prevent corruption if lock holder crashes
- Database locks: Rejected - no database in use
- In-memory locks: Rejected - doesn't work across process boundaries

**Implementation Pattern**:
```python
import fcntl  # Unix
import msvcrt  # Windows
from pathlib import Path

def acquire_file_lock(file_path: Path, timeout: int = 5, retries: int = 3):
    """Cross-platform file locking with timeout and retry."""
    # Platform detection and lock acquisition
    # Retry logic with exponential backoff
    pass
```

### 3. Error Logging Strategy

**Decision**: Write errors to stderr only (no log files)

**Rationale**:
- Clarification answer: stderr logging, process manager captures
- Follows Unix philosophy: stdout for output, stderr for errors
- MCP protocol expects errors in tool responses, not separate log files
- Process managers (systemd, supervisor, Docker) capture stderr automatically
- Keeps codebase simple - no log rotation, file management

**Alternatives Considered**:
- Log files in `.doc-manager/logs/`: Rejected - adds complexity, requires rotation
- Both stderr and files: Rejected - redundant, maintenance burden
- Structured logging framework: Rejected - out of scope for remediation

**Implementation Pattern**:
```python
import sys

def log_error(context: str, error: Exception):
    """Log error to stderr with context."""
    print(f"ERROR [{context}]: {type(error).__name__}: {str(error)}", file=sys.stderr)
```

### 4. Path Traversal Prevention

**Decision**: Multi-layer defense with Path.resolve() + is_relative_to() + symlink detection

**Rationale**:
- FR-001: Reject `..` sequences, absolute paths outside project
- FR-003: Detect and handle symlinks
- Path.resolve() canonicalizes paths (removes `..`, resolves symlinks)
- is_relative_to() verifies resolved path stays within boundary
- is_symlink() detects symlink attacks before resolution

**Alternatives Considered**:
- Regex-based validation only: Rejected - can be bypassed with URL encoding, double encoding
- Whitelist approach: Rejected - too restrictive for legitimate use
- Sandboxing: Rejected - complex, not needed for local-only MCP server

**Implementation Pattern**:
```python
from pathlib import Path

def validate_path_boundary(path: Path, project_root: Path) -> Path:
    """Validate path stays within project boundary."""
    if path.is_symlink():
        # Option 1: Reject symlinks entirely
        raise ValueError("Symlinks not allowed")
        # Option 2: Resolve and verify boundary
        # resolved = path.resolve()
        # if not resolved.is_relative_to(project_root):
        #     raise ValueError("Symlink escapes project boundary")

    resolved = path.resolve()
    if not resolved.is_relative_to(project_root):
        raise ValueError("Path escapes project boundary")

    return resolved
```

### 5. Git Dependency Handling

**Decision**: Fail fast with clear error message if git binary missing

**Rationale**:
- Clarification answer: "Git is required but not found. Please install git."
- Makes dependencies explicit to users
- Avoids silent degradation that confuses users
- Simple implementation - no fallback complexity

**Alternatives Considered**:
- Fall back to checksum-only mode: Rejected - silent degradation confusing
- Detect at server startup: Rejected - affects tools that don't need git
- Bundled git: Rejected - licensing complexity, platform issues

**Implementation Pattern**:
```python
import shutil

def check_git_available():
    """Check if git is available in PATH."""
    if shutil.which('git') is None:
        raise RuntimeError("Git is required but not found. Please install git.")
```

### 6. Response Size Enforcement

**Decision**: Truncate responses at CHARACTER_LIMIT (25,000 chars) with continuation marker

**Rationale**:
- FR-010: Enforce 25,000 character limit from constants.py
- MCP protocol has response size limits
- Large dependency graphs or validation reports can exceed limits
- Truncation with marker allows users to request specific sections

**Alternatives Considered**:
- Pagination: Rejected - requires stateful session, complex for MCP
- Streaming: Rejected - MCP protocol doesn't support streaming responses
- Raise error on size limit: Rejected - better to return partial data than fail

**Implementation Pattern**:
```python
from src.constants import CHARACTER_LIMIT

def enforce_response_limit(response: str) -> str:
    """Truncate response if exceeds CHARACTER_LIMIT."""
    if len(response) <= CHARACTER_LIMIT:
        return response

    truncated = response[:CHARACTER_LIMIT - 100]  # Leave room for marker
    truncated += "\n\n[Response truncated - exceeded 25,000 character limit]"
    return truncated
```

### 7. Resource Limit Enforcement

**Decision**: Implement limits as early-exit checks in traversal loops

**Rationale**:
- FR-019: Max 10,000 files per operation
- FR-020: Max 100 recursion depth
- FR-021: 60-second timeout for file operations
- Early exit prevents resource exhaustion without complex tracking

**Alternatives Considered**:
- Generator-based processing: Considered - better for streaming but complex refactor
- Async task cancellation: Rejected - requires async runtime management
- OS-level limits (ulimit): Rejected - not portable, affects whole process

**Implementation Pattern**:
```python
import signal

def process_files_with_limits(project_path: Path, max_files: int = 10000):
    """Process files with count limit and timeout."""
    def timeout_handler(signum, frame):
        raise TimeoutError("File processing exceeded 60-second limit")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(60)  # 60-second timeout

    try:
        file_count = 0
        for file_path in project_path.rglob("*"):
            if file_count >= max_files:
                raise ValueError(f"File count exceeded limit of {max_files}")

            # Process file...
            file_count += 1
    finally:
        signal.alarm(0)  # Cancel timeout
```

## Technology Stack Decisions

### Pydantic 2.0+ Field Validators

**Why**: Already in use, powerful validation DSL, integrates with FastMCP

**Best Practices**:
- Use `@field_validator` for complex validation logic
- Use `Field(pattern=...)` for simple regex validation
- Use `constr`, `conint` for constrained types
- Raise `ValueError` with descriptive messages

### Python fcntl/msvcrt for File Locking

**Why**: Native OS-level locks, no additional dependencies

**Best Practices**:
- Always use try/finally to release locks
- Implement timeout to prevent deadlocks
- Use exclusive locks (LOCK_EX) for write operations
- Abstract platform differences in utility function

### Git Command Validation

**Why**: Subprocess security critical for command injection prevention

**Best Practices**:
- Always use array form: `subprocess.run(["git", ...])` not `shell=True`
- Validate all user inputs passed to git commands
- Use regex pattern for commit hashes: `^[0-9a-fA-F]{7,40}$`
- Set timeout on all subprocess calls

## Integration Patterns

### MCP Tool Error Handling

All tools follow consistent error handling pattern:

```python
async def tool_name(params: InputModel) -> str:
    try:
        # Tool implementation
        result = perform_operation()
        return format_response(result)
    except Exception as e:
        log_error("tool_name", e)
        return handle_error(e, "tool_name")
```

### Pydantic Model Validation

All models use consistent validation pattern:

```python
class ToolInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    field_name: str = Field(..., min_length=1, max_length=260)

    @field_validator('field_name')
    @classmethod
    def validate_field(cls, v):
        # Validation logic
        return v
```

## Performance Considerations

### File System Operations

- **Current bottleneck**: Sequential checksumming in `initialize_memory`
- **Out of scope**: Parallelization (not part of remediation)
- **Mitigation**: Enforce 10,000 file limit to prevent hangs
- **Future enhancement**: Multiprocessing for checksums

### Regex Compilation

- **Current issue**: Regex compiled in loops (dependencies.py:174-188)
- **Fix**: FR-023 requires compile once, reuse
- **Pattern**: Compile patterns outside loop, pass compiled pattern object

## Security Threat Model

### Threat: Path Traversal Attack

**Attack Vector**: User provides `../../etc/passwd` in documentation links
**Mitigation**: Path.resolve() + is_relative_to() + symlink detection
**Test**: Try various traversal patterns in validation tests

### Threat: Command Injection

**Attack Vector**: User provides `"HEAD; rm -rf /"` as git commit hash
**Mitigation**: Regex validation `^[0-9a-fA-F]{7,40}$` + array-form subprocess
**Test**: Try shell metacharacters in commit hash tests

### Threat: Symlink Attack

**Attack Vector**: Malicious project contains symlink to `/etc/passwd`
**Mitigation**: Detect symlinks with is_symlink(), verify resolved path boundary
**Test**: Create symlinks in test fixtures, verify rejection

### Threat: Resource Exhaustion (DoS)

**Attack Vector**: Extremely large project (millions of files) hangs server
**Mitigation**: File count limit (10K), recursion depth limit (100), timeout (60s)
**Test**: Simulate large project, verify limits enforced

### Threat: ReDoS (Regular Expression Denial of Service)

**Attack Vector**: Complex glob patterns cause exponential regex evaluation time
**Mitigation**: FR-008 requires pattern validation (future: add complexity limit)
**Test**: Try pathological patterns, verify reasonable timeout

## Conclusion

All technical decisions documented with rationale and alternatives considered. No unresolved "NEEDS CLARIFICATION" items remain. Ready to proceed to Phase 1 design.

**Next**: Generate data-model.md (minimal - no new entities), contracts/ (N/A - no API changes), quickstart.md (remediation guide)
