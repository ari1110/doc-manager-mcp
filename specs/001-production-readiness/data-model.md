# Data Model: Production Readiness Remediation

**Feature**: MCP Server Production Readiness
**Date**: 2025-11-15
**Phase**: Phase 1 - Design

## Overview

This remediation project does NOT introduce new entities or data models. Instead, it adds validation rules and constraints to existing Pydantic input models and enhances state file integrity. This document captures the validation schema and constraints being added to existing entities.

## Existing Entities (Being Enhanced)

### 1. Input Validation Models (src/models.py)

These Pydantic models define MCP tool input schemas. Remediation adds field validators to prevent security vulnerabilities.

#### InitializeConfigInput

**Purpose**: Parameters for `docmgr_initialize_config` tool

**Current Fields**:
- `project_path: str` - Path to project root
- `platform: Optional[DocumentationPlatform]` - Doc platform (Hugo, MkDocs, etc.)
- `exclude_patterns: Optional[List[str]]` - Glob patterns to exclude
- `docs_path: Optional[str]` - Relative path to documentation
- `sources: Optional[List[str]]` - Source file patterns
- `response_format: ResponseFormat` - Output format (markdown/json)

**New Validation Rules** (FR-001, FR-006, FR-007):
- `project_path`: min_length=1, max_length=260, no `..` sequences, no absolute paths outside project
- `docs_path`: min_length=1 if provided, no `..` sequences
- `exclude_patterns`: max 50 patterns, each pattern max 512 chars, validate glob syntax
- `sources`: max 50 patterns, each pattern max 512 chars

**Field Validators Added**:
```python
@field_validator('project_path')
@classmethod
def validate_project_path(cls, v):
    if '..' in v:
        raise ValueError('Path traversal not allowed')
    if len(v) > 260:
        raise ValueError('Path exceeds Windows MAX_PATH (260)')
    return v

@field_validator('exclude_patterns')
@classmethod
def validate_patterns(cls, v):
    if v and len(v) > 50:
        raise ValueError('Maximum 50 exclude patterns allowed')
    for pattern in (v or []):
        if len(pattern) > 512:
            raise ValueError(f'Pattern exceeds 512 characters: {pattern[:50]}...')
    return v
```

#### MapChangesInput

**Purpose**: Parameters for `docmgr_map_changes` tool

**Current Fields**:
- `project_path: str` - Path to project root
- `mode: ChangeDetectionMode` - Detection mode (checksum/git_diff)
- `since_commit: Optional[str]` - Git commit hash for comparison
- `response_format: ResponseFormat` - Output format

**New Validation Rules** (FR-002):
- `since_commit`: Must match regex `^[0-9a-fA-F]{7,40}$` if provided (prevents command injection)

**Field Validators Added**:
```python
@field_validator('since_commit')
@classmethod
def validate_commit_hash(cls, v):
    if v is None:
        return v
    import re
    if not re.match(r'^[0-9a-fA-F]{7,40}$', v):
        raise ValueError('Invalid git commit hash format')
    return v
```

#### MigrateInput

**Purpose**: Parameters for `docmgr_migrate` tool

**Current Fields** (FR-024 - CORRECTED FIELD NAMES):
- `project_path: str` - Path to project root
- `existing_docs_path: str` - Source documentation path (was incorrectly accessed as `source_path`)
- `new_docs_path: str` - Target documentation path (was incorrectly accessed as `target_path`)
- `preserve_history: bool` - Whether to preserve git history
- `response_format: ResponseFormat` - Output format

**Bug Fix**: workflows.py:527-528 currently uses `params.source_path` and `params.target_path` but model defines `existing_docs_path` and `new_docs_path`

### 2. Path Boundary Entity

**Purpose**: Represents the security boundary for file system operations

**Attributes**:
- `project_root: Path` - The canonical project root directory
- `docs_root: Optional[Path]` - The documentation directory root (if specified)

**Validation Rules** (FR-001, FR-003):
- All file operations must resolve paths and verify: `resolved_path.is_relative_to(project_root)`
- Symlinks must be detected and either rejected or verified after resolution
- Absolute paths outside project must be rejected

**State**:
- Immutable once established at tool invocation
- Used by all file system operations for boundary checks

### 3. File Lock Entity

**Purpose**: Represents an exclusive lock on `.doc-manager/` state files

**Attributes**:
- `file_path: Path` - Path to file being locked
- `lock_handle: int | None` - OS-specific lock handle (fcntl/msvcrt)
- `timeout: int` - Lock acquisition timeout (5 seconds per clarification)
- `retries: int` - Number of retry attempts (3 per clarification)
- `acquired: bool` - Whether lock is currently held

**Lifecycle**:
1. **Acquire**: Attempt to get exclusive lock with timeout
2. **Retry**: If locked by another process, wait and retry (max 3 times)
3. **Hold**: Perform file operation while lock held
4. **Release**: Always release in finally block

**Implementation** (FR-018):
```python
class FileLock:
    def __init__(self, file_path: Path, timeout: int = 5, retries: int = 3):
        self.file_path = file_path
        self.timeout = timeout
        self.retries = retries
        self.lock_handle = None
        self.acquired = False

    def __enter__(self):
        # Acquire lock with retry logic
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Always release lock
        pass
```

### 4. Error Response Entity

**Purpose**: Standardized error message format returned to MCP clients

**Attributes**:
- `error_type: str` - Exception class name (e.g., "ValueError")
- `context: str` - Tool name or operation context
- `message: str` - Sanitized error message (no sensitive info per FR-017)
- `timestamp: datetime` - When error occurred (logged to stderr)

**Format** (FR-015, FR-016, FR-017):
```python
def handle_error(e: Exception, context: str) -> str:
    """Format error as string for MCP response."""
    error_msg = f"Error: {type(e).__name__}"
    if context:
        error_msg += f" in {context}"
    error_msg += f": {str(e)}"
    # Log to stderr (clarification: stderr only, no log files)
    print(f"[{datetime.now().isoformat()}] {error_msg}", file=sys.stderr)
    return error_msg
```

### 5. Resource Limit Entity

**Purpose**: Enforces operational constraints to prevent resource exhaustion

**Attributes**:
- `max_files: int` - Maximum files to process (10,000 per FR-019)
- `max_depth: int` - Maximum recursion depth (100 per FR-020)
- `timeout: int` - Operation timeout in seconds (60 per FR-021)
- `current_count: int` - Files processed so far
- `current_depth: int` - Current recursion depth

**Validation**:
- Checked at each iteration of file traversal loops
- Raises `ValueError` when limit exceeded
- Timeout enforced via signal.alarm() (Unix) or threading.Timer() (Windows)

### 6. State Files (Enhanced Integrity)

These JSON/YAML files in `.doc-manager/` now require file locking for concurrent access:

#### repo-baseline.json

**Purpose**: Stores file checksums and git metadata

**Schema**:
```json
{
  "version": "1.0.0",
  "timestamp": "ISO-8601-datetime",
  "checksums": {
    "relative/path/to/file.py": "sha256-hex-digest"
  },
  "git": {
    "branch": "main",
    "commit": "commit-hash",
    "remote": "origin-url"
  }
}
```

**Concurrency**: Now requires file lock before read/write (FR-018)

#### dependencies.json

**Purpose**: Stores bidirectional code-to-docs dependency graph

**Schema**:
```json
{
  "doc-to-code": {
    "docs/guide.md": ["src/server.py", "src/tools/config.py"]
  },
  "code-to-docs": {
    "src/server.py": ["docs/guide.md", "docs/api.md"]
  }
}
```

**Concurrency**: Now requires file lock before read/write (FR-018)

## Validation State Machine

### Path Validation Flow

```
User Input (path string)
    ↓
Field Validator (Pydantic)
    ├─ Check min_length ≥ 1
    ├─ Check max_length ≤ 260
    ├─ Check no '..' sequences
    ├─ Check no shell metacharacters
    ↓ [PASS]
Tool Function
    ├─ Convert to Path object
    ├─ Check is_symlink()
    │   ├─ [TRUE] → Reject OR resolve and verify
    │   └─ [FALSE] → Continue
    ├─ Resolve path (Path.resolve())
    ├─ Verify is_relative_to(project_root)
    │   ├─ [TRUE] → SAFE
    │   └─ [FALSE] → REJECT
    ↓ [SAFE]
File Operation Proceeds
```

### File Lock Acquisition Flow

```
Request File Lock
    ↓
Attempt #1 (timeout: 5s)
    ├─ [SUCCESS] → Acquired
    └─ [TIMEOUT] → Wait 1s
        ↓
    Attempt #2 (timeout: 5s)
        ├─ [SUCCESS] → Acquired
        └─ [TIMEOUT] → Wait 1s
            ↓
        Attempt #3 (timeout: 5s)
            ├─ [SUCCESS] → Acquired
            └─ [TIMEOUT] → FAIL
                ↓
            Raise LockTimeout Error
```

## Relationships

### Input Models → Tools

- Each tool has exactly one input model (1:1 mapping)
- Input model validates parameters before tool execution
- Tool trusts validated input (no re-validation needed)

### Tools → State Files

- Multiple tools can read/write same state files
- File locks coordinate concurrent access
- Lock scope: single file (not directory-wide)

### Path Boundary → File Operations

- Every file operation consults path boundary
- Boundary check happens after path resolution
- Symlinks resolved, then boundary-checked

## Data Constraints Summary

| Entity | Constraint Type | Limit | Enforcement |
|--------|----------------|-------|-------------|
| project_path | Length | 1-260 chars | Pydantic Field |
| project_path | Content | No `..` | Field Validator |
| exclude_patterns | Count | Max 50 | Field Validator |
| exclude_patterns | Item length | Max 512 chars | Field Validator |
| since_commit | Format | Regex `^[0-9a-fA-F]{7,40}$` | Field Validator |
| File traversal | Count | Max 10,000 files | Runtime check in loop |
| Recursion | Depth | Max 100 levels | Runtime check in recursion |
| File operation | Timeout | 60 seconds | signal.alarm() |
| File lock | Timeout | 5 seconds × 3 retries | fcntl/msvcrt with retry |
| MCP response | Size | 25,000 characters | Truncation wrapper |

## No New Entities

This remediation adds NO new entities to the data model. All changes are enhancements to existing structures:
- Input validation strengthened
- State file integrity protected with locks
- Security boundaries enforced consistently
- Resource limits added to prevent exhaustion

**Backward Compatibility**: All input model changes are additive (validators, not field changes), maintaining compatibility with existing MCP clients.
