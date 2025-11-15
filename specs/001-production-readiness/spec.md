# Feature Specification: MCP Server Production Readiness Remediation

**Feature Branch**: `001-production-readiness`
**Created**: 2025-11-15
**Status**: Draft
**Input**: User description: "Production readiness remediation for doc-manager MCP server - addressing critical security vulnerabilities, MCP protocol compliance issues, and implementation bugs"

## Clarifications

### Session 2025-11-15

- Q: Error Logging Strategy - FR-015 requires replacing silent error handlers, but where should errors be logged? → A: Write errors to stderr (process manager captures them)
- Q: Git Dependency Failure Mode - What should happen when git binary is completely missing from the system? → A: Fail with clear error message: "Git is required but not found. Please install git."
- Q: File Lock Timeout Behavior - FR-018 requires file locking, but what timeout should be used to prevent deadlocks? → A: 5-second timeout with 3 retry attempts (total ~15 seconds)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure File System Operations (Priority: P1)

Users operating the MCP server must have confidence that the server protects against file system attacks, including path traversal and symlink exploits that could expose sensitive files outside the project boundary.

**Why this priority**: Path traversal vulnerabilities are CRITICAL security risks that can expose credentials, system files, and sensitive user data. This is a production blocker.

**Independent Test**: Can be fully tested by attempting to validate documentation containing malicious paths (e.g., `../../etc/passwd`) and verifying the server rejects or sanitizes them, delivering secure file access without compromising system integrity.

**Acceptance Scenarios**:

1. **Given** a user provides a project path, **When** the MCP server processes files, **Then** it must only access files within the explicitly provided project boundary
2. **Given** documentation contains links with path traversal sequences (`../../../`), **When** the validation tool processes them, **Then** the server must detect and reject or sanitize these paths
3. **Given** a project contains symlinks pointing outside the project directory, **When** the server traverses files, **Then** it must detect symlinks and either reject them or verify resolved paths remain within boundaries
4. **Given** a user provides an absolute path to sensitive files (e.g., `/etc/passwd`), **When** the server resolves paths, **Then** it must reject paths that escape the project root

---

### User Story 2 - Prevent Command Injection (Priority: P1)

Users must be protected from command injection attacks when the MCP server executes git operations with user-provided commit hashes or other parameters.

**Why this priority**: Command injection is a CRITICAL vulnerability that could allow arbitrary code execution on the host system. This is a production blocker.

**Independent Test**: Can be fully tested by providing malicious git commit hashes (e.g., `"HEAD; rm -rf /"`) and verifying the server validates and sanitizes input before subprocess execution, preventing arbitrary command execution.

**Acceptance Scenarios**:

1. **Given** a user provides a git commit hash parameter, **When** the server validates the input, **Then** it must reject hashes that don't match valid git SHA format (7-40 hex characters)
2. **Given** a user provides a commit hash containing shell metacharacters, **When** the server processes the parameter, **Then** it must reject the input before passing to subprocess
3. **Given** a valid commit hash is provided, **When** the server executes git commands, **Then** subprocess calls must use array form (not shell=True) with validated arguments only

---

### User Story 3 - Protect Credential Secrets (Priority: P1)

The MCP server configuration must not expose API keys, tokens, or other credentials in version control or plaintext files accessible to unauthorized parties.

**Why this priority**: Exposed credentials create immediate security breaches and compliance violations. This is a production blocker.

**Independent Test**: Can be fully tested by scanning the repository for plaintext credentials, verifying sensitive config files are properly ignored by version control, and confirming the server reads secrets from secure sources (environment variables) only.

**Acceptance Scenarios**:

1. **Given** the MCP server requires API credentials, **When** configuration is initialized, **Then** credentials must be sourced from environment variables, not plaintext files
2. **Given** configuration files exist (e.g., `.mcp.json`), **When** version control is checked, **Then** these files must be excluded via `.gitignore`
3. **Given** the repository is scanned, **When** searching for credential patterns, **Then** no plaintext API keys, tokens, or passwords must be present in tracked files

---

### User Story 4 - Correct MCP Protocol Implementation (Priority: P2)

MCP clients relying on tool metadata must receive accurate information about tool behavior (read-only vs destructive operations) and properly formatted responses.

**Why this priority**: Incorrect tool hints and response formats break client assumptions and can lead to data loss or corrupted state. This is a HIGH priority issue affecting MCP contract compliance.

**Independent Test**: Can be fully tested by invoking each tool and verifying: (1) tool hints accurately reflect behavior (readOnlyHint matches actual file operations), (2) response sizes stay within MCP limits, (3) JSON/markdown formats are correctly applied, delivering reliable MCP protocol adherence.

**Acceptance Scenarios**:

1. **Given** a tool modifies the file system (writes to `.doc-manager/`), **When** the tool is registered, **Then** its `readOnlyHint` must be set to `False`
2. **Given** a tool returns a response, **When** the response size exceeds the character limit, **Then** the server must truncate or paginate the response appropriately
3. **Given** a tool is configured to return JSON format, **When** the response is generated, **Then** it must be valid JSON without embedded unicode characters that break parsers
4. **Given** a tool encounters an error, **When** formatting the error response, **Then** it must return a properly formatted string (not raise exceptions to MCP layer)

---

### User Story 5 - Comprehensive Input Validation (Priority: P2)

Users providing parameters to MCP tools must have their inputs validated to prevent injection attacks, resource exhaustion, and undefined behavior from malformed data.

**Why this priority**: Missing input validation creates multiple attack vectors (path injection, regex DoS, resource exhaustion) and causes runtime errors. This is a HIGH priority security and stability issue.

**Independent Test**: Can be fully tested by providing edge case and malicious inputs (empty strings, extreme lengths, special characters, invalid patterns) to each tool parameter and verifying appropriate validation errors are returned, preventing undefined behavior.

**Acceptance Scenarios**:

1. **Given** a user provides path parameters, **When** validation runs, **Then** paths must be checked for: minimum length, maximum length (e.g., 260 chars for Windows), absence of path traversal sequences, and valid characters only
2. **Given** a user provides list parameters (exclude_patterns, sources), **When** validation runs, **Then** both list length and individual item length must be constrained
3. **Given** a user provides optional fields, **When** values are None or empty, **Then** the tool must handle these gracefully with documented default behavior
4. **Given** a user provides string enum parameters, **When** validation runs, **Then** values must match allowed enum values exactly (with proper pattern validation)

---

### User Story 6 - Graceful Error Handling (Priority: P3)

Users encountering errors must receive clear, actionable error messages without exposing sensitive system information, and errors must be properly logged for debugging.

**Why this priority**: Poor error handling hides bugs, leaks sensitive information, and makes debugging impossible. This is a MEDIUM priority usability and security issue.

**Independent Test**: Can be fully tested by triggering various error conditions (missing files, invalid configs, permission errors) and verifying: (1) users receive helpful error messages, (2) no stack traces or sensitive paths leak, (3) errors are properly propagated (not silently swallowed), delivering robust error management.

**Acceptance Scenarios**:

1. **Given** a tool encounters an exception, **When** handling the error, **Then** it must return a formatted error string (not silent failure with `except: pass`)
2. **Given** an error message is generated, **When** returned to the user, **Then** it must not expose full file system paths, implementation details, or stack traces
3. **Given** a file operation fails (permission denied, file not found), **When** the error is handled, **Then** the message must provide actionable guidance (e.g., "Run docmgr_initialize_memory first")
4. **Given** concurrent tool calls modify shared state, **When** race conditions occur, **Then** the server must detect conflicts and return appropriate errors (not corrupt data)

---

### User Story 7 - Resource Exhaustion Protection (Priority: P3)

The MCP server must protect against denial-of-service attacks and accidental resource exhaustion from processing extremely large projects or malicious inputs.

**Why this priority**: Unbounded operations can hang the server, consume excessive memory/CPU, and impact other users. This is a MEDIUM priority stability and availability issue.

**Independent Test**: Can be fully tested by processing projects with edge case characteristics (millions of files, deeply nested directories, large file counts) and verifying the server enforces timeouts, file count limits, and recursion depth limits, preventing resource exhaustion.

**Acceptance Scenarios**:

1. **Given** a tool traverses the file system, **When** processing files, **Then** it must enforce limits on: total files processed (e.g., max 10,000), recursion depth (e.g., max 100 levels), and operation timeout (e.g., max 60 seconds)
2. **Given** a tool processes exclude patterns or regex, **When** complex patterns are provided, **Then** the server must validate patterns for ReDoS (Regular Expression Denial of Service) vulnerabilities
3. **Given** a tool computes checksums or builds dependency graphs, **When** processing large file sets, **Then** memory usage must remain bounded (e.g., streaming processing, not loading all in memory)
4. **Given** concurrent tool invocations access shared resources, **When** file locks are needed, **Then** lock acquisition must timeout after 5 seconds with 3 retries to prevent deadlocks

---

### Edge Cases

- What happens when a user provides a project path that exists but has no read permissions?
- How does the system handle symbolic links that create circular references?
- What happens when exclude patterns conflict with source patterns (mutual exclusion)?
- How does the server respond when git commands are invoked in a non-git repository?
- What happens when the git binary is not installed or not in PATH? (Answer: Fail with clear error message)
- What happens when JSON responses exceed MCP protocol size limits?
- How does the system handle concurrent modifications to `.doc-manager/` state files?
- What happens when file system changes occur between validation checks and actual use (TOCTOU race conditions)?
- How does the server handle unicode/emoji characters in file paths and content?
- What happens when a tool's parameter model attributes don't match the actual input fields (AttributeError)?
- How does the system handle extremely long paths that exceed OS limits (Windows MAX_PATH = 260)?

## Requirements *(mandatory)*

### Functional Requirements

**Security & Input Validation:**

- **FR-001**: System MUST validate all path inputs to reject path traversal sequences (`..`, absolute paths outside project root)
- **FR-002**: System MUST validate git commit hash inputs using regex pattern `^[0-9a-fA-F]{7,40}$`
- **FR-003**: System MUST detect and handle symlinks by either rejecting them or verifying resolved targets remain within project boundaries
- **FR-004**: System MUST source all credentials (API keys, tokens) from environment variables, never from plaintext configuration files
- **FR-005**: System MUST exclude sensitive configuration files (`.mcp.json`, `.env`) from version control via `.gitignore`
- **FR-006**: System MUST validate all string inputs with both minimum length (≥1 for paths) and maximum length (≤260 for paths) constraints
- **FR-007**: System MUST validate list parameters with constraints on both list length (max 50 items) and individual item length (max 512 chars)
- **FR-008**: System MUST validate exclude patterns and source patterns to prevent ReDoS attacks

**MCP Protocol Compliance:**

- **FR-009**: Tools that modify file system state MUST set `readOnlyHint=False` in tool registration
- **FR-010**: System MUST enforce character limits on all tool responses (max 25,000 characters as defined in constants)
- **FR-011**: Tools returning JSON format MUST exclude unicode/emoji characters that break JSON parsers
- **FR-012**: System MUST wrap all JSON serialization in error handling to catch non-serializable types
- **FR-013**: System MUST return all errors as properly formatted strings (not raise exceptions to MCP layer)
- **FR-014**: Tool parameter names in implementation MUST match field names in Pydantic input models exactly

**Error Handling:**

- **FR-015**: System MUST replace all silent error handlers (`except: pass`) with proper error logging to stderr or user-facing error messages
- **FR-016**: Error messages MUST provide actionable guidance (e.g., "Run X tool first", "Check file permissions")
- **FR-017**: Error messages MUST NOT expose full file system paths, stack traces, or implementation details
- **FR-018**: System MUST implement file locking for all operations modifying `.doc-manager/` state files with 5-second timeout and 3 retry attempts

**Resource Protection:**

- **FR-019**: File system traversal operations MUST enforce maximum file count limit (default: 10,000 files)
- **FR-020**: Recursive operations MUST enforce maximum recursion depth (default: 100 levels)
- **FR-021**: All blocking operations MUST implement configurable timeouts (default: 60 seconds for file operations)
- **FR-022**: File processing MUST use streaming or bounded memory patterns (not load all files in memory)
- **FR-023**: Regex compilation MUST be performed outside loops (compile once, reuse)

**Tool Implementation Correctness:**

- **FR-024**: Tool `workflows.py` MUST use correct parameter attribute names matching MigrateInput model
- **FR-025**: Tool `validation.py` MUST verify resolved link targets remain within documentation root
- **FR-026**: Tool `dependencies.py` MUST implement precise reference matching (not substring matching causing false positives)
- **FR-027**: Tool `memory.py` and `changes.py` MUST respect exclude_patterns configuration (not use hardcoded exclusions only)
- **FR-028**: All file system operations MUST check symlink status before processing
- **FR-029**: Line number calculations in validation reports MUST be accurate (no off-by-one errors)
- **FR-030**: Quality score calculations MUST handle invalid scores gracefully (not default silently)

### Key Entities

- **Tool**: A registered MCP tool with defined inputs, outputs, and behavior hints (readOnlyHint, destructiveHint, idempotentHint)
- **Input Validation Model**: Pydantic BaseModel defining parameter schemas with constraints (min_length, max_length, pattern)
- **Path Boundary**: The project root directory defining the security boundary for all file system operations
- **Credential**: Sensitive authentication data (API keys, tokens) that must never be stored in plaintext or version control
- **Error Response**: Formatted string returned to MCP client containing actionable error information without sensitive details
- **Resource Limit**: Configurable constraint (file count, recursion depth, timeout, memory) preventing resource exhaustion
- **State File**: JSON/YAML files in `.doc-manager/` directory requiring file locking for concurrent access

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Security:**

- **SC-001**: System successfully rejects 100% of path traversal attack attempts in validation tests
- **SC-002**: System successfully validates and rejects 100% of malformed git commit hash inputs
- **SC-003**: Repository scan finds zero exposed credentials or API keys in tracked files
- **SC-004**: All configuration files containing secrets are verified to be in `.gitignore`
- **SC-005**: System successfully detects and handles symlinks in 100% of test cases without escaping project boundaries

**MCP Compliance:**

- **SC-006**: All tool `readOnlyHint` values accurately reflect actual file system modification behavior (0% mismatches)
- **SC-007**: 100% of tool responses stay within the 25,000 character limit (or properly paginated)
- **SC-008**: 100% of JSON responses are valid JSON without unicode parsing errors
- **SC-009**: All 10 MCP tools execute without raising exceptions to the MCP layer (100% error handling coverage)
- **SC-010**: Server runtime produces zero AttributeError exceptions from parameter name mismatches

**Input Validation:**

- **SC-011**: All path inputs are validated with minimum length, maximum length, and character constraints (100% coverage)
- **SC-012**: All list parameters enforce both item count and individual item length limits (100% coverage)
- **SC-013**: System handles edge case inputs (None, empty string, whitespace, extreme lengths) gracefully in 100% of tests

**Error Handling:**

- **SC-014**: Zero instances of silent error handling (`except: pass`) remain in production code
- **SC-015**: 100% of error messages provide actionable guidance to users
- **SC-016**: Error messages expose zero sensitive information (paths, stack traces, implementation details) in user-facing output

**Resource Protection:**

- **SC-017**: System enforces file count limits and prevents processing projects with >10,000 files without explicit override
- **SC-018**: All blocking operations complete or timeout within configured time limits (100% timeout compliance)
- **SC-019**: Memory usage remains bounded when processing large projects (no unbounded list/dict growth)

**Testability:**

- **SC-020**: Feature achieves test pyramid targets: 70% unit tests, 20% integration tests, 10% end-to-end tests
- **SC-021**: All 30 functional requirements have corresponding test coverage (100% requirement coverage)
- **SC-022**: Security test suite includes dedicated tests for path traversal, command injection, symlink attacks, and credential exposure

**Overall System Stability:**

- **SC-023**: MCP server operates without crashes or unhandled exceptions for 100 consecutive tool invocations in stress testing
- **SC-024**: Concurrent tool invocations (10 simultaneous calls) complete without data corruption or deadlocks
- **SC-025**: System processes representative projects (small, medium, large) within acceptable time limits (small <5s, medium <30s, large <60s with limits)

## Assumptions

1. **Git Availability**: Assumed git is installed and available in PATH for git-related operations
2. **File System Permissions**: Assumed the server runs with appropriate read/write permissions for project directories
3. **Environment Configuration**: Assumed users can set environment variables for credential configuration
4. **MCP Client Compliance**: Assumed MCP clients properly handle tool responses up to 25,000 characters
5. **Python Version**: Assumed Python 3.10+ is available as specified in project dependencies
6. **Single Server Instance**: Assumed one MCP server instance per project (though must handle concurrent tool calls within that instance)
7. **Trusted Project Source**: Assumed project directories are from trusted sources (not untrusted/malicious third-party repos)
8. **Standard Platforms**: Assumed operation on standard platforms (Windows, macOS, Linux) with standard path conventions

## Out of Scope

The following are explicitly **out of scope** for this remediation work:

1. **Development Infrastructure**: CI/CD pipelines, GitHub Actions, deployment automation
2. **Documentation Updates**: README improvements, API documentation generation, contribution guidelines
3. **Performance Optimization**: Advanced caching, parallelization, incremental processing beyond resource limits
4. **Monitoring/Observability**: Logging frameworks, metrics collection, distributed tracing
5. **Version Management**: Semantic versioning, git tags, changelog generation, release processes
6. **Test Infrastructure**: Test pyramid rebalancing (reducing integration tests, adding more unit tests)
7. **Build Tooling**: Dockerization, Makefiles, build scripts
8. **New Features**: Any functionality beyond fixing existing tool implementations
9. **Multi-tenancy**: Support for multiple users/projects with authentication/authorization
10. **Distributed Deployment**: Scaling beyond single-server, single-instance deployment

These items may be addressed in separate specifications but are not part of production readiness remediation.

## Dependencies

**External Dependencies:**
- Pydantic >=2.0.0 (for enhanced field validators)
- Python standard library: pathlib, re, subprocess, json, yaml, hashlib

**Internal Dependencies:**
- Existing MCP server implementation in `server.py`
- Current tool implementations in `src/tools/*.py`
- Pydantic models in `src/models.py`
- Constants and utilities in `src/constants.py` and `src/utils.py`

**Configuration Dependencies:**
- `.gitignore` must be updated to exclude sensitive files
- Environment must provide credential configuration (environment variables)

**No Breaking Changes:**
- All fixes must maintain backward compatibility with existing MCP tool interfaces
- Input model changes must only add validations, not remove/rename fields
