# Observations & Follow-up Items

## Performance & Response Issues

### 1. Bootstrap tool response not returned (2025-11-16)
**Observation**: `docmgr_bootstrap` completed successfully (created all files) but returned empty response (`Tool ran without output or errors`).

**Details**:
- Tool execution: ~4 minutes (13:51 to 13:55)
- Files created successfully:
  - `.doc-manager.yml`
  - `docs/` structure with templates
  - `.doc-manager/memory/repo-baseline.json` (188 files checksummed)
- No error occurred, but response markdown/json never returned to client

**Impact**: User doesn't see completion report or next steps

**Potential causes**:
- FastMCP response size limit?
- Async response handling issue?
- Timeout in MCP protocol layer?

**Follow-up**:
- [ ] Test with smaller repo to see if response comes through
- [ ] Check FastMCP documentation for response size limits
- [ ] Add response size logging to debug
- [ ] Consider streaming responses for long operations

### 2. Bootstrap performance (2025-11-16)
**Observation**: Bootstrap took ~4 minutes for 116-file repo

**Details**:
- Operation timeout: 60s per tool
- Bootstrap calls 5 sequential operations:
  1. Platform detection
  2. Config creation
  3. Docs structure creation
  4. Memory initialization (checksums 116 files)
  5. Quality assessment
- Memory initialization likely the slowest step

**Impact**: Poor user experience for larger repos

**Follow-up**:
- [ ] Profile each step to identify bottleneck
- [ ] Consider making memory initialization optional/async
- [ ] Add progress indicators for long operations
- [ ] Optimize file checksumming (parallel processing?)

### 3. Tool responses are double-encoded JSON strings (2025-11-16)
**Observation**: Tool responses are returned as stringified JSON inside a `result` wrapper, unlike standard MCP servers.

**Details**:
- **Our tools return**:
  ```json
  {"result": "{\"key\": \"value\", \"nested\": \"data\"}"}
  ```
  (JSON string with escaped `\n` characters)

- **Standard MCP servers return** (e.g., exa):
  ```json
  {"key": "value", "nested": "data"}
  ```
  (Actual structured JSON)

**Impact**:
- Harder to parse responses (requires JSON.parse twice)
- Inconsistent with MCP ecosystem conventions
- `\n` characters appear as literal escapes instead of formatting

**Root cause**:
- Tools return strings (via `safe_json_dumps()` or markdown formatting)
- FastMCP wraps string responses in `{"result": "..."}` envelope
- Should return actual Python dicts/objects instead

**Follow-up**:
- [ ] Investigate FastMCP response handling
- [ ] Consider returning structured data instead of pre-formatted strings
- [ ] Check if response_format parameter should control serialization layer
- [ ] Review MCP spec for response format guidelines

## Refactoring Completed

### ✅ MCP tool handlers now use direct parameters (2025-11-16)
- All 10 tools refactored from `params: InputModel` to direct parameters
- Matches standard MCP pattern (like exa)
- Enum conversions working correctly
- Commit: da59991

## Testing Progress

### Tested Successfully ✅
- [x] `docmgr_detect_platform` - Returns platform recommendation
- [x] `docmgr_bootstrap` - Creates docs/config/memory (slow, no response) ⚠️
- [x] `docmgr_validate_docs` - Validates links/assets/snippets
- [x] `docmgr_assess_quality` - Assesses quality criteria (list-of-enum works)
- [x] `docmgr_track_dependencies` - Builds dependency graph
- [x] `docmgr_map_changes` - Detects code changes (enum conversion works)
- [x] `docmgr_sync` - Recommends doc updates based on changes

### Tested Indirectly (called by bootstrap)
- [x] `docmgr_initialize_config` - Creates .doc-manager.yml
- [x] `docmgr_initialize_memory` - Creates memory baseline

### Not Tested
- [ ] `docmgr_migrate` - Requires existing docs to migrate from

### Key Validation
- ✅ Direct parameters working (no more params wrapper)
- ✅ Enum conversions working (ResponseFormat, DocumentationPlatform, ChangeDetectionMode)
- ✅ List-of-enum conversion working (criteria parameter)
- ✅ Boolean parameters working (check_links, check_assets, etc.)
- ✅ Optional parameters working (docs_path, platform, etc.)
