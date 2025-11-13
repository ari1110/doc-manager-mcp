# Next Steps for Doc-Manager MCP Server

## Current Status

**Implemented (3/10 tools):**
- ✅ `docmgr_initialize_config` - Configuration file creation
- ✅ `docmgr_initialize_memory` - Memory system with checksum tracking
- ✅ `docmgr_detect_platform` - Platform detection and recommendations

**Repository:** `R:/mcp-servers/doc-manager`
**Latest Commit:** `00cc0f1` - Add uv.lock to gitignore
**Lines of Code:** ~1,056 lines across modular structure

---

## Remaining Work

### 1. Enhance Platform Detection

**Priority:** Medium
**File:** `src/tools/platform.py`

**Improvements Needed:**
- Implement hybrid detection approach:
  1. Check root-level configs (current implementation - fast path)
  2. Search common doc directories (`docsite/`, `docs/`, `documentation/`, `website/`) - targeted search
  3. Parse dependency files (`package.json`, `go.mod`, etc.) to detect platform from dependencies
  4. Limit recursive search depth to 3 levels for performance

**Example Enhancement:**
```python
# Add after root-level checks
doc_dirs = ["docsite", "docs", "documentation", "website", "site"]
for doc_dir in doc_dirs:
    doc_path = project_path / doc_dir
    if doc_path.exists():
        # Check for Hugo
        if (doc_path / "hugo.yaml").exists() or (doc_path / "hugo.toml").exists():
            detected_platforms.append({...})
        # ... similar checks for other platforms
```

### 2. Implement Quality Assessment Tool

**Priority:** High
**File:** `src/tools/quality.py` (new file)
**Model:** Already defined in `src/models.py` - `AssessQualityInput`

**Requirements:**
- Evaluate documentation against 7 quality criteria:
  1. **Relevance** - Addresses current user needs and use cases
  2. **Accuracy** - Reflects actual codebase state
  3. **Purposefulness** - Clear goals and target audience
  4. **Uniqueness** - No redundant or conflicting information
  5. **Consistency** - Terminology, formatting, and structure align
  6. **Clarity** - Precise language, concrete examples, intuitive navigation
  7. **Structure** - Logical organization with appropriate depth

**Implementation Approach:**
- Integrate Vale CLI for prose linting (consistency, clarity)
- Implement custom checkers for other criteria
- Generate quality report with scores and specific issues
- Support both JSON and Markdown output formats

**Tool Registration:**
```python
@mcp.tool(
    name="docmgr_assess_quality",
    annotations={
        "title": "Assess Documentation Quality",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_assess_quality(params: AssessQualityInput) -> str:
    """Evaluate documentation against 7 quality criteria."""
    return await assess_quality(params)
```

**Reference:** See `R:\Test-Projects\pass-cli\.claude\skills\documentation-manager\references\quality-criteria.md` for detailed rubrics.

### 3. Implement Validation Tool

**Priority:** High
**File:** `src/tools/validation.py` (new file)
**Model:** Already defined - `ValidateDocsInput`

**Validation Checks:**
1. **Broken Links**
   - Internal links (markdown references, relative paths)
   - External links (HTTP/HTTPS URLs)
   - Generate report with file:line references

2. **Asset Validation**
   - Verify all image links point to existing files
   - Check for missing alt text on images
   - Identify unused assets (in manifest but not referenced)

3. **Code Snippet Validation**
   - Extract code blocks from markdown
   - Attempt to compile/lint by language
   - Flag syntax errors with file:line references

**Example Implementation:**
```python
async def validate_docs(params: ValidateDocsInput) -> str:
    issues = []

    if params.check_links:
        issues.extend(await _check_broken_links(docs_path))

    if params.check_assets:
        issues.extend(await _validate_assets(docs_path, asset_manifest))

    if params.check_snippets:
        issues.extend(await _validate_code_snippets(docs_path))

    return _format_validation_report(issues, params.response_format)
```

### 4. Implement Change Mapping Tool

**Priority:** High
**File:** `src/tools/changes.py` (new file)
**Model:** Already defined - `MapChangesInput`

**Functionality:**
- Compare current file checksums vs. memory baseline
- Identify changed files and their scope (API, CLI, config, internal)
- Map changes to affected documentation files
- Use `doc-mapping-patterns.md` reference for common mappings

**Example Mappings:**
- `cmd/tui/*.go` changed → Update `docs/guides/tui-guide.md`
- `internal/vault/*.go` changed → Update `docs/reference/security-architecture.md`
- `go.mod` dependencies changed → Update `docs/getting-started/installation.md`

**Output:**
```json
{
  "changes_detected": true,
  "changed_files": ["cmd/tui/model.go", "cmd/tui/view.go"],
  "affected_docs": [
    {
      "file": "docs/guides/tui-guide.md",
      "reason": "TUI implementation changes in cmd/tui/",
      "priority": "high"
    }
  ]
}
```

### 5. Implement Dependency Tracking Tool

**Priority:** Medium
**File:** `src/tools/dependencies.py` (new file)
**Model:** Already defined - `TrackDependenciesInput`

**Functionality:**
- Build a dependency graph of code → docs relationships
- Track which docs depend on which code files/APIs
- Useful for impact analysis before making code changes

**Implementation:**
- Parse documentation for code references (file paths, function names, etc.)
- Cross-reference with actual codebase
- Store dependency graph in `.doc-manager/dependencies.json`

### 6. Implement Bootstrap Workflow

**Priority:** High
**File:** `src/tools/workflows.py` (new file)
**Model:** Already defined - `BootstrapInput`

**Workflow Steps:**
1. Detect platform (call `detect_platform`)
2. Create docs structure from templates (`assets/structure/`)
3. Generate initial documentation files with placeholders
4. Set up platform-specific configuration
5. Initialize memory system
6. Run initial quality assessment

**Template Structure to Create:**
Create `assets/structure/` with basic docs skeleton:
```
assets/structure/
├── README.md (template)
├── docs/
│   ├── _index.md (template)
│   ├── getting-started/
│   │   └── installation.md (template)
│   ├── guides/
│   │   └── quick-start.md (template)
│   └── reference/
│       └── api.md (template)
```

### 7. Implement Migration Workflow

**Priority:** High
**File:** `src/tools/workflows.py`
**Model:** Already defined - `MigrateInput`

**Workflow Steps:**
1. Assess existing documentation (call `assess_quality`)
2. Detect existing platform
3. Create new parallel docs directory
4. Map old structure → new structure
5. Use `git mv` to preserve history (if `preserve_history=true`)
6. Generate breaking changes report
7. Update internal links and references

**Breaking Changes Handling:**
- Track all moved/renamed files
- Generate redirect mappings
- Report broken links with suggested fixes
- Create migration guide document

### 8. Implement Sync Workflow

**Priority:** High
**File:** `src/tools/workflows.py`
**Model:** Already defined - `SyncInput`

**Sync Modes:**

**Reactive Mode** (manual trigger):
1. Map changes since last sync (call `map_changes`)
2. Identify affected documentation
3. Present proposed updates to user
4. Apply updates
5. Update memory checksums

**Proactive Mode** (auto-detect):
1. Run on every code change (via git hook or CI)
2. Automatically detect impacts
3. Generate PR/commit with doc updates
4. Or: flag docs as needing review

**Implementation:**
- Use checksum comparison (more robust than git commit hashes)
- Support both modes in single tool
- Generate detailed sync report

### 9. Create Supporting Reference Files

**Priority:** Medium
**Location:** Create these in the skill directory for reference

Files to create:
1. **`doc-platform-selector.md`** - Decision framework for choosing platforms
2. **`doc-mapping-patterns.md`** - Common code change → doc update patterns
3. **`breaking-changes-handling.md`** - Systematic approach to migration
4. **`dependency-tracking-patterns.md`** - How to identify doc-code dependencies

### 10. Add Monorepo Support

**Priority:** Low (future enhancement)
**Files:** All workflow tools

**Enhancements Needed:**
- Parse `.doc-manager.yml` for `projects` array
- Scope all operations to specific project
- Structure memory per-project: `.doc-manager/project-a/memory/`
- Allow targeting specific project in tool calls

**Example Config:**
```yaml
projects:
  - 'packages/app-frontend'
  - 'services/user-api'
```

**Example Tool Call:**
```json
{
  "project_path": "R:/monorepo",
  "project": "packages/app-frontend"
}
```

### 11. Add CI/CD Integration Scripts

**Priority:** Medium
**File:** `src/tools/ci.py` (new file)

**Scripts to Create:**
1. **Pre-commit Hook**
   - Validate docs before commit
   - Check for broken links
   - Ensure code examples are valid

2. **PR Check**
   - Run validation on documentation changes
   - Generate quality report
   - Comment on PR with findings

3. **Merge Check**
   - Final validation before merge
   - Update memory system
   - Sync docs if needed

### 12. Create Comprehensive Tests

**Priority:** High
**File:** `tests/` (new directory)

**Test Coverage:**
1. Unit tests for each utility function
2. Integration tests for each tool
3. End-to-end workflow tests
4. Test with real repositories (pass-cli as test case)

**Example Test Structure:**
```
tests/
├── unit/
│   ├── test_utils.py
│   ├── test_models.py
│   └── test_constants.py
├── integration/
│   ├── test_config_tool.py
│   ├── test_memory_tool.py
│   ├── test_platform_tool.py
│   └── test_quality_tool.py
└── fixtures/
    └── sample_project/
```

### 13. Create MCP Evaluation Tests

**Priority:** Medium
**File:** `evaluations/` (new directory)

According to mcp-builder skill, create evaluation XML:
```xml
<evaluation>
  <qa_pair>
    <question>Initialize documentation for a Go project and detect the platform</question>
    <answer>hugo</answer>
  </qa_pair>
  <!-- More test cases -->
</evaluation>
```

### 14. Documentation and Publishing

**Priority:** Low (after all tools complete)

**Tasks:**
1. Update README.md with all 10 tools documented
2. Add usage examples for each tool
3. Create CONTRIBUTING.md
4. Add LICENSE file
5. Create changelog (CHANGELOG.md)
6. Publish to GitHub
7. Consider PyPI package publication
8. Add to MCP servers directory

---

## Suggested Implementation Order

### Phase 1: Core Validation & Quality (Week 1)
1. Enhance platform detection (subdirectory search)
2. Implement validation tool
3. Implement quality assessment tool
4. Create supporting reference files

### Phase 2: Change Tracking (Week 2)
1. Implement change mapping tool
2. Implement dependency tracking tool
3. Add comprehensive tests

### Phase 3: Workflows (Week 3)
1. Implement bootstrap workflow
2. Implement migrate workflow
3. Implement sync workflow
4. Create evaluation tests

### Phase 4: Advanced Features (Week 4)
1. Add CI/CD integration scripts
2. Add monorepo support
3. Create comprehensive documentation
4. Publish and share

---

## Technical Debt to Address

1. **Error Handling:** Add more specific error types beyond generic `Exception`
2. **Performance:** Add caching for expensive operations (checksums, file scanning)
3. **Progress Reporting:** Add progress callbacks for long operations
4. **Logging:** Add structured logging for debugging
5. **Configuration Validation:** Validate `.doc-manager.yml` schema on load

---

## Resources and References

**Existing Code:**
- Quality criteria rubrics: `R:\Test-Projects\pass-cli\.claude\skills\documentation-manager\references\quality-criteria.md`
- MCP best practices: `R:\Test-Projects\pass-cli\.claude\skills\mcp-builder\reference\mcp_best_practices.md`
- Python MCP guide: `R:\Test-Projects\pass-cli\.claude\skills\mcp-builder\reference\python_mcp_server.md`

**External Tools to Integrate:**
- Vale CLI: https://vale.sh/ (prose linting)
- Link checkers: Python `linkchecker` or similar
- Language-specific linters (pylint, eslint, etc.)

**Testing:**
- MCP Inspector: `npx @modelcontextprotocol/inspector uv run python server.py`
- Test project: `R:\Test-Projects\pass-cli`

---

## Questions to Answer

1. **Vale Integration:** Should Vale be a required dependency or optional?
2. **Platform Templates:** Should we bundle platform-specific templates or generate them dynamically?
3. **Async Operations:** Should long operations (checksumming, validation) be truly async with progress updates?
4. **API Design:** Should workflows return structured data or human-readable reports?
5. **Monorepo Priority:** Should monorepo support be in initial release or v2.0?

---

## Success Criteria

The doc-manager MCP server is complete when:

1. ✅ All 10 tools implemented and tested
2. ✅ Works with uv and pip installation
3. ✅ Comprehensive test coverage (>80%)
4. ✅ Evaluation tests pass
5. ✅ Documentation complete with examples
6. ✅ Successfully manages documentation for pass-cli project
7. ✅ Can detect, validate, and sync docs automatically
8. ✅ Generates quality reports with actionable insights

---

**Last Updated:** 2025-01-13
**Current Version:** 0.1.0
**Target Version:** 1.0.0
