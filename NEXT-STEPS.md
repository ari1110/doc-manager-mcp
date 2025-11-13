# Next Steps for Doc-Manager MCP Server

## Current Status

**Implemented (3/10 tools):**
- ✅ `docmgr_initialize_config` - Configuration file creation
- ✅ `docmgr_initialize_memory` - Memory system with checksum tracking
- ✅ `docmgr_detect_platform` - Platform detection and recommendations

**Repository:** `R:/mcp-servers/doc-manager`
**Latest Commit:** `00cc0f1` - Add uv.lock to gitignore
**Lines of Code:** ~1,056 lines across modular structure

## Quick Start for Developers

**New to this project?** Start here:

1. **Read IMPLEMENTATION-GUIDE.md** - Step-by-step instructions with code examples for each tool
2. **Use templates/** - Copy templates for new tools, tests, and workflows
3. **Reference references/** - Decision frameworks and pattern guides
4. **Follow the phase plan below** - Systematic implementation order

**Key Resources:**
- `IMPLEMENTATION-GUIDE.md` - Detailed implementation guide with code skeletons
- `templates/tools/tool-template.py` - Standard tool structure
- `templates/tests/test-template.py` - Pytest template with fixtures
- `templates/tools/workflow-template.py` - Workflow orchestration pattern
- `references/quality-criteria.md` - 7 quality criteria rubrics
- `references/doc-mapping-patterns.md` - 8 code→doc mapping patterns
- `references/doc-platform-selector.md` - Platform selection decision tree

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

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Tool 1: Quality Assessment

**Requirements:**
- Evaluate documentation against 7 quality criteria:
  1. **Relevance** - Addresses current user needs and use cases
  2. **Accuracy** - Reflects actual codebase state
  3. **Purposefulness** - Clear goals and target audience
  4. **Uniqueness** - No redundant or conflicting information
  5. **Consistency** - Terminology, formatting, and structure align
  6. **Clarity** - Precise language, concrete examples, intuitive navigation
  7. **Structure** - Logical organization with appropriate depth

**Quick Start:**
1. Copy `templates/tools/tool-template.py` to `src/tools/quality.py`
2. Implement `_assess_criterion()` for each quality criterion
3. Integrate Vale CLI for consistency/clarity checks (optional)
4. Register tool in `server.py` using the pattern from IMPLEMENTATION-GUIDE.md
5. Create tests using `templates/tests/test-template.py`

**Reference:** `references/quality-criteria.md` for detailed rubrics and assessment questions.

### 3. Implement Validation Tool

**Priority:** High
**File:** `src/tools/validation.py` (new file)
**Model:** Already defined - `ValidateDocsInput`

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Tool 2: Validation

**Validation Checks:**
1. **Broken Links** - Internal/external links, file:line references
2. **Asset Validation** - Image existence, alt text, unused assets
3. **Code Snippet Validation** - Extract and lint code blocks by language

**Quick Start:**
1. Copy `templates/tools/tool-template.py` to `src/tools/validation.py`
2. Implement link checker using code from IMPLEMENTATION-GUIDE.md
3. Implement asset validator using `_extract_markdown_images()` utility
4. Implement snippet validator with language-specific checks
5. Add utility functions from IMPLEMENTATION-GUIDE.md to `src/utils.py`:
   - `extract_markdown_links()`
   - `extract_markdown_images()`
   - `extract_code_blocks()`
   - `is_url_accessible()`
6. Register tool in `server.py`

### 4. Implement Change Mapping Tool

**Priority:** High
**File:** `src/tools/changes.py` (new file)
**Model:** Already defined - `MapChangesInput`

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Tool 3: Change Mapping

**Functionality:**
- Compare current checksums vs. memory baseline
- Map code changes to affected documentation files
- Apply pattern-based heuristics for intelligent mapping

**Quick Start:**
1. Copy `templates/tools/tool-template.py` to `src/tools/changes.py`
2. Implement checksum comparison logic from IMPLEMENTATION-GUIDE.md
3. Use mapping patterns from `references/doc-mapping-patterns.md`
4. Support custom mappings from `.doc-manager.yml` config
5. Generate report with file paths and priority levels

**Reference:** `references/doc-mapping-patterns.md` for 8 pattern categories (CLI commands, API changes, config changes, dependencies, examples, tests, docs, infrastructure)

### 5. Implement Dependency Tracking Tool

**Priority:** Medium
**File:** `src/tools/dependencies.py` (new file)
**Model:** Already defined - `TrackDependenciesInput`

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Tool 4: Dependency Tracking

**Functionality:**
- Build dependency graph: code files → documentation files
- Extract code references from markdown (file paths, function names)
- Store in `.doc-manager/dependencies.json` for impact analysis

**Quick Start:**
1. Copy `templates/tools/tool-template.py` to `src/tools/dependencies.py`
2. Implement `_extract_code_references()` to parse markdown
3. Use example code from IMPLEMENTATION-GUIDE.md
4. Save dependency graph to JSON file
5. Register tool in `server.py`

### 6. Implement Bootstrap Workflow

**Priority:** High
**File:** `src/tools/workflows.py` (new file)
**Model:** Already defined - `BootstrapInput`

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Tool 5-7: Workflows (Bootstrap section)

**Workflow Steps:**
1. Detect/validate platform
2. Create documentation structure
3. Generate initial content from templates
4. Initialize memory system

**Quick Start:**
1. Copy `templates/tools/workflow-template.py` to `src/tools/workflows.py`
2. Implement `bootstrap()` function using example from IMPLEMENTATION-GUIDE.md
3. Orchestrate existing tools (detect_platform, initialize_memory)
4. Create `assets/structure/` templates for common doc types
5. Register tool in `server.py`

### 7. Implement Migration Workflow

**Priority:** High
**File:** `src/tools/workflows.py`
**Model:** Already defined - `MigrateInput`

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Tool 5-7: Workflows

**Workflow Steps:**
1. Assess existing docs → 2. Detect platform → 3. Map old→new structure → 4. Preserve history (git mv) → 5. Update links → 6. Generate migration report

**Quick Start:**
1. Add `migrate()` function to `src/tools/workflows.py`
2. Use workflow template pattern from `templates/tools/workflow-template.py`
3. Implement backup/rollback logic for safety
4. Track moved files for redirect generation
5. Register tool in `server.py`

### 8. Implement Sync Workflow

**Priority:** High
**File:** `src/tools/workflows.py`
**Model:** Already defined - `SyncInput`

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Tool 5-7: Workflows

**Sync Modes:**
- **Reactive:** Manual trigger → map changes → identify affected docs → update
- **Proactive:** Auto-detect via git hook/CI → generate PR with doc updates

**Quick Start:**
1. Add `sync()` function to `src/tools/workflows.py`
2. Use `map_changes` tool to identify affected docs
3. Implement checksum update logic
4. Support both reactive and proactive modes
5. Register tool in `server.py`

### 9. Create Supporting Reference Files

**Priority:** ~~Medium~~ ✅ **COMPLETED**

**Status:** All reference files created in `references/` directory:
- ✅ `references/quality-criteria.md` - 7 quality criteria rubrics
- ✅ `references/doc-mapping-patterns.md` - 8 code→doc mapping patterns
- ✅ `references/doc-platform-selector.md` - Platform selection decision tree

**Future additions** (if needed):
- `breaking-changes-handling.md` - Migration best practices
- `dependency-tracking-patterns.md` - Code reference extraction patterns

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

**Implementation Guide:** See IMPLEMENTATION-GUIDE.md → Testing Each Tool

**Test Coverage:**
1. Unit tests for utilities
2. Integration tests for each tool
3. End-to-end workflow tests
4. Real repository testing (pass-cli)

**Quick Start:**
1. Copy `templates/tests/test-template.py` for each tool
2. Customize fixtures for specific tool needs
3. Run with: `pytest tests/integration/test_<tool>.py -v`
4. Use pass-cli as integration test case

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

**Local Resources (This Repository):**
- 📘 `IMPLEMENTATION-GUIDE.md` - Comprehensive implementation guide with code examples
- 📂 `templates/` - Tool, test, and workflow templates
- 📚 `references/` - Quality criteria, mapping patterns, platform selector

**Templates:**
- `templates/tools/tool-template.py` - Standard tool structure
- `templates/tests/test-template.py` - Pytest template with fixtures
- `templates/tools/workflow-template.py` - Workflow orchestration pattern

**References:**
- `references/quality-criteria.md` - 7 quality criteria rubrics
- `references/doc-mapping-patterns.md` - 8 code→doc mapping patterns
- `references/doc-platform-selector.md` - Platform decision framework

**External Tools:**
- Vale CLI: https://vale.sh/ (prose linting)
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
