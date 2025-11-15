# API Contracts

**Feature**: Production Readiness Remediation
**Date**: 2025-11-15

## No New API Contracts

This remediation project does **NOT introduce new API endpoints or modify existing MCP tool interfaces**. All 10 MCP tools maintain their current signatures to ensure backward compatibility.

## Existing MCP Tool Interfaces (Unchanged)

The following MCP tools exist and are NOT being modified at the interface level:

1. `docmgr_initialize_config(InitializeConfigInput) -> str`
2. `docmgr_initialize_memory(InitializeMemoryInput) -> str`
3. `docmgr_detect_platform(DetectPlatformInput) -> str`
4. `docmgr_validate_docs(ValidateDocsInput) -> str`
5. `docmgr_assess_quality(AssessQualityInput) -> str`
6. `docmgr_map_changes(MapChangesInput) -> str`
7. `docmgr_track_dependencies(TrackDependenciesInput) -> str`
8. `docmgr_bootstrap(BootstrapInput) -> str`
9. `docmgr_migrate(MigrateInput) -> str`
10. `docmgr_sync(SyncInput) -> str`

## What IS Changing

### Input Validation (Internal)

Pydantic input models are gaining **field validators** that enforce:
- Path traversal prevention (FR-001)
- Commit hash format validation (FR-002)
- List length and item constraints (FR-007)

**Impact**: Invalid inputs that previously passed validation will now be rejected with clear error messages. This is a **security improvement**, not a breaking change.

### Tool Hints (Metadata Only)

Two tools have incorrect `readOnlyHint` values being corrected:
- `docmgr_map_changes`: Currently `True`, should be `False` (writes to `.doc-manager/`)
- `docmgr_track_dependencies`: Currently `True`, should be `False` (writes to `.doc-manager/`)

**Impact**: MCP clients that rely on tool hints will get accurate information about side effects. This is a **bug fix**, not a breaking change.

### Response Format (Unchanged)

All tools continue to return `str` (either JSON or Markdown based on `response_format` parameter).

## MCP Protocol Compliance

This remediation ensures the doc-manager MCP server correctly implements MCP 1.0.0+ protocol:
- Tool registration with accurate hints ✅
- Response size limits enforced (25,000 chars) ✅
- Proper error formatting (no raised exceptions to MCP layer) ✅
- Valid JSON/Markdown responses ✅

## Backward Compatibility Guarantee

Per the specification (Dependencies section):
> **No Breaking Changes**: All fixes must maintain backward compatibility with existing MCP tool interfaces. Input model changes must only add validations, not remove/rename fields.

This means:
- ✅ Existing MCP clients will continue to work
- ✅ Tool names unchanged
- ✅ Input parameter names unchanged
- ✅ Output format unchanged
- ✅ Only **stricter validation** (rejects previously-invalid inputs)

## Future API Changes (Out of Scope)

The following are explicitly out of scope for this remediation:
- New MCP tools
- Modified tool parameters
- New response formats
- API versioning

These would require separate specifications if needed.
